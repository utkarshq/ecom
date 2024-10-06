from decimal import Decimal

from django.db import transaction
from django.db.models import Exists, F, OuterRef, Q

from ....celeryconf import app
from ....discount.models import OrderDiscount, Voucher
from ...models import Order, OrderLine

# The batch of size 250 takes ~0.2 second and consumes ~20MB memory at peak
ORDER_SET_SHIPPING_PRICE_BATCH_SIZE = 250


@app.task
def set_udniscounted_base_shipping_price_on_orders_task():
    qs = Order.objects.filter(undiscounted_base_shipping_price_amount__isnull=True)
    order_ids = list(
        qs.values_list("pk", flat=True)[:ORDER_SET_SHIPPING_PRICE_BATCH_SIZE]
    )
    if order_ids:
        orders = Order.objects.filter(id__in=order_ids)

        # get orders created from checkout that has shipping discount
        # for draft orders the `base_shipping_price_amount` is the undiscounted price
        # so we can use it as a base for the undiscounted price
        orders_with_shipping_discount = _get_orders_with_shipping_discount(orders)

        orders_no_shipping_discount = orders.exclude(
            Exists(orders_with_shipping_discount.filter(pk=OuterRef("pk")))
        )

        if orders_no_shipping_discount:
            _set_undiscounted_base_shipping_price(orders_no_shipping_discount)
        if orders_with_shipping_discount:
            _calculate_and_set_undiscounted_base_shipping_price(
                orders_with_shipping_discount
            )

        set_udniscounted_base_shipping_price_on_orders_task.delay()


def _get_orders_with_shipping_discount(orders):
    orders_with_shipping_voucher = _get_orders_with_shipping_voucher(orders)
    orders_with_shipping_voucher_no_voucher_instance = (
        _get_orders_with_shipping_voucher_no_voucher_instance(orders)
    )
    return (
        orders_with_shipping_voucher | orders_with_shipping_voucher_no_voucher_instance
    )


def _get_orders_with_shipping_voucher(orders):
    shipping_vouchers = Voucher.objects.filter(type="shipping")
    return orders.filter(
        origin__in=["checkout"],
        voucher_code__isnull=False,
        voucher__isnull=False,
    ).filter(Exists(shipping_vouchers.filter(pk=OuterRef("voucher_id"))))


def _get_orders_with_shipping_voucher_no_voucher_instance(orders):
    # lines with applied line voucher
    lines_with_voucher = OrderLine.objects.filter(voucher_code__isnull=False)

    # lines without applied order voucher on line
    # this excludes the cases when entire order voucher was applied
    # (for `ENTIRE_ORDER` voucher type, the voucher_code is stored on the order itself,
    # not on the line, but the discount is propagated to the line level and it's visible
    # in the `unit_price`)
    # - `base_unit_price_amount` is the price with the sale and line voucher applied
    # - `unit_price` is the price with all discounts applied - sales,
    # line and order voucher
    lines_with_not_applicable_voucher = OrderLine.objects.filter(
        Q(voucher_code__isnull=True)
        & (
            Q(base_unit_price_amount=F("unit_price_net_amount"))
            | Q(base_unit_price_amount=F("unit_price_gross_amount"))
        )
    )

    # order discount must be present for such orders
    order_discounts = OrderDiscount.objects.filter(
        order_id__in=orders.values("pk"), type="voucher"
    )

    # orders with voucher code, no voucher instance, without line vouchers
    # and not applicable order voucher
    return (
        orders.filter(
            origin__in=["checkout"],
            voucher_code__isnull=False,
            voucher__isnull=True,
        )
        .exclude(Exists(lines_with_voucher.filter(order_id=OuterRef("pk"))))
        .filter(
            Exists(lines_with_not_applicable_voucher.filter(order_id=OuterRef("pk")))
        )
        .filter(Exists(order_discounts.filter(order_id=OuterRef("pk"))))
    )


def _calculate_and_set_undiscounted_base_shipping_price(orders):
    order_discounts = OrderDiscount.objects.filter(
        order_id__in=orders.values("pk"), type="voucher"
    )
    order_to_discount_amount = {
        order_discount["order_id"]: order_discount["amount_value"]
        for order_discount in order_discounts.values("order_id", "amount_value")
    }
    for order in orders:
        order.undiscounted_base_shipping_price_amount = (
            order.base_shipping_price_amount
            + order_to_discount_amount.get(order.pk, Decimal("0.0"))
        )
    with transaction.atomic():
        _orders = list(orders.select_for_update(of=(["self"])))
        Order.objects.bulk_update(orders, ["undiscounted_base_shipping_price_amount"])


def _set_undiscounted_base_shipping_price(orders):
    with transaction.atomic():
        _orders = list(orders.select_for_update(of=(["self"])))
        orders.update(
            undiscounted_base_shipping_price_amount=F("base_shipping_price_amount")
        )


@app.task
def set_udniscounted_base_shipping_price_on_draft_orders_task():
    qs = Order.objects.filter(
        undiscounted_base_shipping_price_amount=0,
        base_shipping_price_amount__gt=0,
        status="draft",
    )
    order_ids = list(
        qs.values_list("pk", flat=True)[:ORDER_SET_SHIPPING_PRICE_BATCH_SIZE]
    )
    if order_ids:
        orders = Order.objects.filter(id__in=order_ids)
        _set_undiscounted_base_shipping_price(orders)
        set_udniscounted_base_shipping_price_on_draft_orders_task.delay()
