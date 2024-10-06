import datetime
from decimal import Decimal
from unittest.mock import call, patch

import pytest
import pytz
from django.test import override_settings
from django.utils import timezone
from freezegun import freeze_time

from ...core.models import EventDelivery
from ...core.utils.events import call_event_including_protected_events
from ...plugins.manager import get_plugins_manager
from ...tests.utils import flush_post_commit_hooks
from ...webhook.event_types import WebhookEventAsyncType, WebhookEventSyncType
from .. import CheckoutAuthorizeStatus, CheckoutChargeStatus
from ..actions import (
    call_checkout_event,
    call_checkout_events,
    call_checkout_info_event,
    transaction_amounts_for_checkout_updated,
)
from ..calculations import fetch_checkout_data
from ..fetch import fetch_checkout_info, fetch_checkout_lines


@patch("saleor.plugins.manager.PluginsManager.checkout_fully_paid")
def test_transaction_amounts_for_checkout_updated_fully_paid(
    mocked_fully_paid, checkout_with_items, transaction_item_generator, plugins_manager
):
    # given
    checkout = checkout_with_items
    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(checkout_info, plugins_manager, lines)
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=checkout_info.checkout.total.gross.amount
    )

    # when
    transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then
    flush_post_commit_hooks()
    checkout.refresh_from_db()
    assert checkout.charge_status == CheckoutChargeStatus.FULL
    assert checkout.authorize_status == CheckoutAuthorizeStatus.FULL
    mocked_fully_paid.assert_called_with(checkout, webhooks=set())


@patch("saleor.plugins.manager.PluginsManager.checkout_fully_paid")
def test_transaction_amounts_for_checkout_updated_with_already_fully_paid(
    mocked_fully_paid, checkout_with_items, transaction_item_generator, plugins_manager
):
    # given
    checkout = checkout_with_items
    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(checkout_info, plugins_manager, lines)
    transaction_item_generator(
        checkout_id=checkout.pk, charged_value=checkout_info.checkout.total.gross.amount
    )

    fetch_checkout_data(checkout_info, plugins_manager, lines, force_status_update=True)

    second_transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=checkout_info.checkout.total.gross.amount
    )
    # when
    transaction_amounts_for_checkout_updated(
        second_transaction, manager=plugins_manager
    )

    # then
    flush_post_commit_hooks()
    checkout.refresh_from_db()
    assert checkout.charge_status == CheckoutChargeStatus.OVERCHARGED
    assert checkout.authorize_status == CheckoutAuthorizeStatus.FULL
    assert not mocked_fully_paid.called


@pytest.mark.parametrize(
    "previous_modified_at",
    [None, datetime.datetime(2018, 5, 31, 12, 0, 0, tzinfo=pytz.UTC)],
)
@patch("saleor.plugins.manager.PluginsManager.checkout_fully_paid")
@freeze_time("2023-05-31 12:00:01")
def test_transaction_amounts_for_checkout_updated_updates_last_transaction_modified_at(
    mocked_fully_paid,
    previous_modified_at,
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.last_transaction_modified_at = previous_modified_at
    checkout.save(update_fields=["last_transaction_modified_at"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=checkout_info.checkout.total.gross.amount
    )

    # when
    transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then
    flush_post_commit_hooks()
    checkout.refresh_from_db()
    assert checkout.last_transaction_modified_at == transaction.modified_at
    mocked_fully_paid.assert_called_with(checkout, webhooks=set())


def test_get_checkout_refundable_with_transaction_and_last_refund_success(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10.0)
    )

    # when
    transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is True


def test_get_checkout_refundable_with_transaction_and_last_refund_failure(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.automatically_refundable = True
    checkout.save(update_fields=["automatically_refundable"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10.0), last_refund_success=False
    )

    # when
    transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is False


def test_get_checkout_refundable_with_transaction_without_funds(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.automatically_refundable = True
    checkout.save(update_fields=["automatically_refundable"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(0)
    )

    # when
    transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is False


def test_get_checkout_refundable_with_multiple_transactions_without_funds(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.automatically_refundable = True
    checkout.save(update_fields=["automatically_refundable"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    first_transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(0)
    )
    transaction_item_generator(checkout_id=checkout.pk, charged_value=Decimal(0))

    # when
    transaction_amounts_for_checkout_updated(first_transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is False


def test_get_checkout_refundable_with_multiple_transactions_with_failure_refund(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.automatically_refundable = True
    checkout.save(update_fields=["automatically_refundable"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    first_transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10), last_refund_success=False
    )
    transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10), last_refund_success=False
    )

    # when
    transaction_amounts_for_checkout_updated(first_transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is False


def test_get_checkout_refundable_with_multiple_active_transactions(
    checkout_with_items,
    transaction_item_generator,
    plugins_manager,
):
    # given
    checkout = checkout_with_items
    checkout.automatically_refundable = True
    checkout.save(update_fields=["automatically_refundable"])

    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(
        checkout_info,
        plugins_manager,
        lines,
    )
    first_transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10), last_refund_success=False
    )
    transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10), last_refund_success=True
    )
    transaction_item_generator(
        checkout_id=checkout.pk, charged_value=Decimal(10), last_refund_success=True
    )

    # when
    transaction_amounts_for_checkout_updated(first_transaction, manager=plugins_manager)

    # then
    checkout.refresh_from_db()
    assert checkout.automatically_refundable is True


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_event_incorrect_webhook_event(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    incorrect_event = WebhookEventAsyncType.ORDER_UPDATED
    # when

    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(
            ValueError,
            match=f"Event {incorrect_event} not found in CHECKOUT_WEBHOOK_EVENT_MAP.",
        ):
            call_checkout_event(
                plugins_manager,
                incorrect_event,
                checkout_with_items,
            )

    # then
    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_event_triggers_sync_webhook_when_needed(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_CREATED,
                checkout_with_items,
            )

    # then
    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.get(webhook_id=tax_webhook.id)
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(tax_delivery),
        ]
    )
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created,
        checkout_with_items,
        webhooks={checkout_created_webhook},
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_event_skips_tax_webhook_when_not_expired(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now() + datetime.timedelta(hours=1)
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        call_checkout_event(
            plugins_manager,
            WebhookEventAsyncType.CHECKOUT_CREATED,
            checkout_with_items,
        )

    # then
    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.filter(webhook_id=tax_webhook.id).first()
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not tax_delivery
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
        ]
    )
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created,
        checkout_with_items,
        webhooks={checkout_created_webhook},
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_event_skip_sync_webhooks_when_async_missing(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []

    # setup sync webhooks with async that is not going to be called
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_UPDATED,
                checkout_with_items,
            )

    # then

    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_event_only_async_when_sync_missing(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    permission_manage_checkouts,
    settings,
    webhook,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    webhook.events.create(event_type=WebhookEventAsyncType.CHECKOUT_CREATED)
    webhook.app.permissions.add(permission_manage_checkouts)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_CREATED,
                checkout_with_items,
            )

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(webhook_id=webhook.id)

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not mocked_send_webhook_request_sync.called
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created, checkout_with_items, webhooks={webhook}
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_info_event_incorrect_webhook_event(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    lines_info, _ = fetch_checkout_lines(
        checkout_with_items,
    )
    checkout_info = fetch_checkout_info(
        checkout_with_items,
        lines_info,
        plugins_manager,
    )
    incorrect_webhook_event = WebhookEventAsyncType.ORDER_UPDATED

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(
            ValueError,
            match=f"Event {incorrect_webhook_event} not found in CHECKOUT_WEBHOOK_EVENT_MAP.",
        ):
            call_checkout_info_event(
                plugins_manager,
                incorrect_webhook_event,
                checkout_info,
                lines_info,
            )

    # then
    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_info_event_triggers_sync_webhook_when_needed(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    lines_info, _ = fetch_checkout_lines(
        checkout_with_items,
    )
    checkout_info = fetch_checkout_info(
        checkout_with_items,
        lines_info,
        plugins_manager,
    )

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_info_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_CREATED,
                checkout_info,
                lines_info,
            )

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.get(webhook_id=tax_webhook.id)
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(tax_delivery),
        ]
    )
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created,
        checkout_with_items,
        webhooks={checkout_created_webhook},
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_info_event_skips_tax_webhook_when_not_expired(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now() + datetime.timedelta(hours=1)
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    lines_info, _ = fetch_checkout_lines(
        checkout_with_items,
    )
    checkout_info = fetch_checkout_info(
        checkout_with_items,
        lines_info,
        plugins_manager,
    )

    # when
    with django_capture_on_commit_callbacks(execute=True):
        call_checkout_info_event(
            plugins_manager,
            WebhookEventAsyncType.CHECKOUT_CREATED,
            checkout_info,
            lines_info,
        )

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.filter(webhook_id=tax_webhook.id).first()
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not tax_delivery
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
        ]
    )
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created,
        checkout_with_items,
        webhooks={checkout_created_webhook},
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_info_event_only_async_when_sync_missing(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    permission_manage_checkouts,
    settings,
    webhook,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    webhook.events.create(event_type=WebhookEventAsyncType.CHECKOUT_CREATED)
    webhook.app.permissions.add(permission_manage_checkouts)

    lines_info, _ = fetch_checkout_lines(
        checkout_with_items,
    )
    checkout_info = fetch_checkout_info(
        checkout_with_items,
        lines_info,
        plugins_manager,
    )

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_info_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_CREATED,
                checkout_info,
                lines_info,
            )

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(webhook_id=webhook.id)

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not mocked_send_webhook_request_sync.called
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_created, checkout_with_items, webhooks={webhook}
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_info_event_skip_sync_webhooks_when_async_missing(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []

    # setup sync webhooks with async that is not going to be called
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    lines_info, _ = fetch_checkout_lines(
        checkout_with_items,
    )
    checkout_info = fetch_checkout_info(
        checkout_with_items,
        lines_info,
        plugins_manager,
    )

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_info_event(
                plugins_manager,
                WebhookEventAsyncType.CHECKOUT_UPDATED,
                checkout_info,
                lines_info,
            )

    # then

    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch(
    "saleor.checkout.actions.call_checkout_info_event",
    wraps=call_checkout_info_event,
)
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_transaction_amounts_for_checkout_fully_paid_triggers_sync_webhook(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    wrapped_call_checkout_info_event,
    setup_checkout_webhooks,
    settings,
    checkout_with_items,
    transaction_item_generator,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now() - datetime.timedelta(hours=10)
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_fully_paid_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_FULLY_PAID)
    checkout = checkout_with_items
    lines, _ = fetch_checkout_lines(checkout)
    checkout_info = fetch_checkout_info(checkout, lines, plugins_manager)
    checkout_info, _ = fetch_checkout_data(checkout_info, plugins_manager, lines)
    transaction = transaction_item_generator(
        checkout_id=checkout.pk, charged_value=checkout_info.checkout.total.gross.amount
    )

    # when
    with django_capture_on_commit_callbacks(execute=True):
        transaction_amounts_for_checkout_updated(transaction, manager=plugins_manager)

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_fully_paid_delivery = EventDelivery.objects.get(
        webhook_id=checkout_fully_paid_webhook.id
    )
    tax_delivery = EventDelivery.objects.get(webhook_id=tax_webhook.id)
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_fully_paid_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(tax_delivery),
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
        ]
    )
    assert wrapped_call_checkout_info_event.called
    mocked_call_event_including_protected_events.assert_called_once_with(
        plugins_manager.checkout_fully_paid,
        checkout_with_items,
        webhooks={checkout_fully_paid_webhook},
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_events_incorrect_webhook_event(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    incorrect_event = WebhookEventAsyncType.ORDER_UPDATED
    # when

    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(
            ValueError,
            match=f"Events { {incorrect_event} } not found in CHECKOUT_WEBHOOK_EVENT_MAP.",
        ):
            call_checkout_events(
                plugins_manager,
                [incorrect_event, WebhookEventAsyncType.CHECKOUT_CREATED],
                checkout_with_items,
            )

    # then
    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_events_triggers_sync_webhook_when_needed(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_events(
                plugins_manager,
                [
                    WebhookEventAsyncType.CHECKOUT_CREATED,
                    WebhookEventAsyncType.CHECKOUT_UPDATED,
                ],
                checkout_with_items,
            )

    # then
    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.get(webhook_id=tax_webhook.id)
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(tax_delivery),
        ]
    )
    mocked_call_event_including_protected_events.assert_has_calls(
        [
            call(
                plugins_manager.checkout_created,
                checkout_with_items,
                webhooks={checkout_created_webhook},
            ),
            call(plugins_manager.checkout_updated, checkout_with_items, webhooks=set()),
        ]
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_events_skips_tax_webhook_when_not_expired(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    settings,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now() + datetime.timedelta(hours=1)
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []
    (
        tax_webhook,
        shipping_webhook,
        shipping_filter_webhook,
        checkout_created_webhook,
    ) = setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        call_checkout_events(
            plugins_manager,
            [
                WebhookEventAsyncType.CHECKOUT_CREATED,
                WebhookEventAsyncType.CHECKOUT_UPDATED,
            ],
            checkout_with_items,
        )

    # then
    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(
        webhook_id=checkout_created_webhook.id
    )
    tax_delivery = EventDelivery.objects.filter(webhook_id=tax_webhook.id).first()
    filter_shipping_delivery = EventDelivery.objects.get(
        webhook_id=shipping_filter_webhook.id,
        event_type=WebhookEventSyncType.CHECKOUT_FILTER_SHIPPING_METHODS,
    )
    shipping_methods_delivery = EventDelivery.objects.get(
        webhook_id=shipping_webhook.id,
        event_type=WebhookEventSyncType.SHIPPING_LIST_METHODS_FOR_CHECKOUT,
    )

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not tax_delivery
    mocked_send_webhook_request_sync.assert_has_calls(
        [
            call(shipping_methods_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
            call(filter_shipping_delivery, timeout=settings.WEBHOOK_SYNC_TIMEOUT),
        ]
    )
    mocked_call_event_including_protected_events.assert_has_calls(
        [
            call(
                plugins_manager.checkout_created,
                checkout_with_items,
                webhooks={checkout_created_webhook},
            ),
            call(plugins_manager.checkout_updated, checkout_with_items, webhooks=set()),
        ]
    )


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_events_skip_sync_webhooks_when_async_missing(
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    setup_checkout_webhooks,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    mocked_send_webhook_request_sync.return_value = []

    # setup sync webhooks with async that is not going to be called
    setup_checkout_webhooks(WebhookEventAsyncType.CHECKOUT_CREATED)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_events(
                plugins_manager,
                [
                    WebhookEventAsyncType.CHECKOUT_FULLY_PAID,
                    WebhookEventAsyncType.CHECKOUT_UPDATED,
                ],
                checkout_with_items,
            )

    # then

    assert not mocked_send_webhook_request_async.called
    assert not mocked_send_webhook_request_sync.called


@freeze_time("2023-05-31 12:00:01")
@patch("saleor.webhook.transport.synchronous.transport.send_webhook_request_sync")
@patch(
    "saleor.webhook.transport.asynchronous.transport.send_webhook_request_async.apply_async"
)
@patch(
    "saleor.checkout.actions.call_event_including_protected_events",
    wraps=call_event_including_protected_events,
)
@override_settings(PLUGINS=["saleor.plugins.webhook.plugin.WebhookPlugin"])
def test_call_checkout_events_only_async_when_sync_missing(
    mocked_call_event_including_protected_events,
    mocked_send_webhook_request_async,
    mocked_send_webhook_request_sync,
    checkout_with_items,
    permission_manage_checkouts,
    settings,
    webhook,
    django_capture_on_commit_callbacks,
):
    # given
    plugins_manager = get_plugins_manager(allow_replica=False)
    checkout_with_items.price_expiration = timezone.now()
    checkout_with_items.save(update_fields=["price_expiration"])

    webhook.events.create(event_type=WebhookEventAsyncType.CHECKOUT_CREATED)
    webhook.app.permissions.add(permission_manage_checkouts)

    # when
    with django_capture_on_commit_callbacks(execute=True):
        with freeze_time("2023-06-01 12:00:01"):
            call_checkout_events(
                plugins_manager,
                [
                    WebhookEventAsyncType.CHECKOUT_CREATED,
                    WebhookEventAsyncType.CHECKOUT_UPDATED,
                ],
                checkout_with_items,
            )

    # then

    # confirm that event delivery was generated for each webhook.
    checkout_create_delivery = EventDelivery.objects.get(webhook_id=webhook.id)

    mocked_send_webhook_request_async.assert_called_once_with(
        kwargs={"event_delivery_id": checkout_create_delivery.id},
        queue=settings.CHECKOUT_WEBHOOK_EVENTS_CELERY_QUEUE_NAME,
        bind=True,
        retry_backoff=10,
        retry_kwargs={"max_retries": 5},
    )
    assert not mocked_send_webhook_request_sync.called
    mocked_call_event_including_protected_events.assert_has_calls(
        [
            call(
                plugins_manager.checkout_created,
                checkout_with_items,
                webhooks={webhook},
            ),
            call(plugins_manager.checkout_updated, checkout_with_items, webhooks=set()),
        ]
    )
