import json
from unittest.mock import patch

import graphene
import pytest

from .....app.error_codes import AppErrorCode
from .....webhook.error_codes import WebhookErrorCode
from .....webhook.models import Webhook
from ....tests.utils import assert_no_permission, get_graphql_content
from ...enums import WebhookEventTypeAsyncEnum, WebhookEventTypeSyncEnum

WEBHOOK_CREATE = """
    mutation webhookCreate($input: WebhookCreateInput!){
      webhookCreate(input: $input) {
        errors {
          field
          message
          code
        }
        webhook {
          id
          asyncEvents {
            eventType
          }
          syncEvents {
            eventType
          }
        }
      }
    }
"""


def test_webhook_create_by_app(app_api_client, permission_manage_orders):
    # given
    query = WEBHOOK_CREATE
    custom_headers = {"X-Key": "Value", "Authorization-Key": "Value"}
    variables = {
        "input": {
            "name": "New integration",
            "targetUrl": "https://www.example.com",
            "asyncEvents": [
                WebhookEventTypeAsyncEnum.ORDER_CREATED.name,
                WebhookEventTypeAsyncEnum.ORDER_CREATED.name,
            ],
            "customHeaders": json.dumps(custom_headers),
        }
    }

    # when
    response = app_api_client.post_graphql(
        query,
        variables=variables,
        permissions=[permission_manage_orders],
        check_no_permissions=False,
    )
    get_graphql_content(response)

    # then
    new_webhook = Webhook.objects.get()
    assert new_webhook.filterable_channel_slugs == []
    assert new_webhook.name == "New integration"
    assert new_webhook.target_url == "https://www.example.com"
    assert new_webhook.custom_headers == {
        "x-key": "Value",
        "authorization-key": "Value",
    }
    events = new_webhook.events.all()
    assert len(events) == 1
    assert events[0].event_type == WebhookEventTypeAsyncEnum.ORDER_CREATED.value


def test_webhook_create_inactive_app(app_api_client, app, permission_manage_orders):
    # given
    app.is_active = False
    app.save()
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "name": "",
        }
    }
    # when
    response = app_api_client.post_graphql(
        query, variables=variables, permissions=[permission_manage_orders]
    )
    # then
    assert_no_permission(response)


def test_webhook_create_without_app(app_api_client, app):
    # given
    app_api_client.app = None
    app_api_client.app_token = None
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "name": "",
        }
    }
    # when
    response = app_api_client.post_graphql(query, variables=variables)
    # then
    assert_no_permission(response)


def test_webhook_create_app_doesnt_exist(app_api_client, app):
    # given
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "name": "",
        }
    }
    # when
    app.delete()
    response = app_api_client.post_graphql(query, variables=variables)
    # then
    assert_no_permission(response)


def test_webhook_create_by_staff(
    staff_api_client,
    app,
    permission_manage_apps,
    permission_manage_orders,
):
    # given
    query = WEBHOOK_CREATE
    app.permissions.add(permission_manage_orders)
    app_id = graphene.Node.to_global_id("App", app.pk)
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "syncEvents": [WebhookEventTypeSyncEnum.PAYMENT_LIST_GATEWAYS.name],
            "app": app_id,
        }
    }
    staff_api_client.user.user_permissions.add(permission_manage_apps)

    # when
    response = staff_api_client.post_graphql(query, variables=variables)
    get_graphql_content(response)

    # then
    new_webhook = Webhook.objects.get()
    assert new_webhook.filterable_channel_slugs == []
    assert new_webhook.target_url == "https://www.example.com"
    assert new_webhook.app == app
    events = new_webhook.events.all()
    assert len(events) == 2

    created_event_types = [events[0].event_type, events[1].event_type]
    assert WebhookEventTypeAsyncEnum.ORDER_CREATED.value in created_event_types
    assert WebhookEventTypeSyncEnum.PAYMENT_LIST_GATEWAYS.value in created_event_types


def test_webhook_create_by_staff_with_inactive_app(staff_api_client, app):
    # given
    app.is_active = False
    query = WEBHOOK_CREATE
    app_id = graphene.Node.to_global_id("App", app.pk)
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "app": app_id,
        }
    }

    # when
    response = staff_api_client.post_graphql(query, variables=variables)
    assert_no_permission(response)

    # then
    assert Webhook.objects.count() == 0


def test_webhook_create_by_staff_without_permission(staff_api_client, app):
    # given
    query = WEBHOOK_CREATE
    app_id = graphene.Node.to_global_id("App", app.pk)
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "app": app_id,
        }
    }

    # when
    response = staff_api_client.post_graphql(query, variables=variables)

    # then
    assert_no_permission(response)
    assert Webhook.objects.count() == 0


def test_webhook_create_by_app_invalid_query(app_api_client, permission_manage_orders):
    # given
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "name": "New integration",
            "targetUrl": "https://www.example.com",
            "asyncEvents": [
                WebhookEventTypeAsyncEnum.ORDER_CREATED.name,
            ],
            "query": "invalid_query",
        }
    }

    # when
    response = app_api_client.post_graphql(
        query,
        variables=variables,
        permissions=[permission_manage_orders],
        check_no_permissions=False,
    )
    content = get_graphql_content(response)

    # then
    data = content["data"]["webhookCreate"]
    assert not data["webhook"]
    error = data["errors"][0]
    assert error["field"] == "query"
    assert 'Unexpected Name "invalid_query"' in error["message"]
    assert error["code"] == WebhookErrorCode.SYNTAX.name


def test_webhook_create_by_staff_for_removed_app(
    staff_api_client,
    removed_app,
    permission_manage_apps,
):
    # given
    query = WEBHOOK_CREATE
    app_id = graphene.Node.to_global_id("App", removed_app.pk)
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "asyncEvents": [WebhookEventTypeAsyncEnum.ORDER_CREATED.name],
            "syncEvents": [WebhookEventTypeSyncEnum.PAYMENT_LIST_GATEWAYS.name],
            "app": app_id,
        }
    }
    staff_api_client.user.user_permissions.add(permission_manage_apps)

    # when
    response = staff_api_client.post_graphql(query, variables=variables)

    # then
    content = get_graphql_content(response)
    app_data = content["data"]["webhookCreate"]
    assert app_data["webhook"] is None
    assert app_data["errors"][0]["code"] == AppErrorCode.NOT_FOUND.name
    assert app_data["errors"][0]["field"] == "app"


SUBSCRIPTION_QUERY_WITH_MULTIPLE_EVENTS = """
subscription {
  event {
    ... on PaymentListGateways {
      checkout {
        id
      }
    }
    ... on OrderCreated {
      order {
        id
      }
    }
  }
}
"""


def test_webhook_create_inherit_events_from_query(
    staff_api_client,
    app,
    permission_manage_apps,
    permission_manage_orders,
):
    # given
    query = WEBHOOK_CREATE
    app.permissions.add(permission_manage_orders)
    staff_api_client.user.user_permissions.add(permission_manage_apps)
    app_id = graphene.Node.to_global_id("App", app.pk)
    variables = {
        "input": {
            "targetUrl": "https://www.example.com",
            "app": app_id,
            "query": SUBSCRIPTION_QUERY_WITH_MULTIPLE_EVENTS,
        }
    }

    # when
    response = staff_api_client.post_graphql(query, variables=variables)
    content = get_graphql_content(response)

    # then
    new_webhook = Webhook.objects.get()
    assert new_webhook.target_url == "https://www.example.com"
    assert new_webhook.app == app
    assert new_webhook.filterable_channel_slugs == []
    events = new_webhook.events.all()
    assert len(events) == 2

    created_event_types = [event.event_type for event in events]
    assert WebhookEventTypeAsyncEnum.ORDER_CREATED.value in created_event_types
    assert WebhookEventTypeSyncEnum.PAYMENT_LIST_GATEWAYS.value in created_event_types

    data = content["data"]["webhookCreate"]
    assert not data["errors"]
    assert data["webhook"]
    assert (
        data["webhook"]["asyncEvents"][0]["eventType"]
        == WebhookEventTypeAsyncEnum.ORDER_CREATED.name
    )
    assert (
        data["webhook"]["syncEvents"][0]["eventType"]
        == WebhookEventTypeSyncEnum.PAYMENT_LIST_GATEWAYS.name
    )


def test_webhook_create_invalid_custom_headers(app_api_client):
    # given
    query = WEBHOOK_CREATE
    custom_headers = {"DisallowedKey": "Value"}
    variables = {
        "input": {
            "name": "New integration",
            "targetUrl": "https://www.example.com",
            "customHeaders": json.dumps(custom_headers),
        }
    }

    # when
    response = app_api_client.post_graphql(query, variables=variables)
    content = get_graphql_content(response)

    # then
    data = content["data"]["webhookCreate"]
    assert not data["webhook"]
    error = data["errors"][0]
    assert error["field"] == "customHeaders"
    assert (
        error["message"] == '"DisallowedKey" does not match allowed key pattern: '
        '"X-*", "Authorization*", or "BrokerProperties".'
    )
    assert error["code"] == WebhookErrorCode.INVALID_CUSTOM_HEADERS.name


def test_webhook_create_notify_user_with_another_event(app_api_client):
    # given
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "name": "NOTIFY_USER with another event fails to save",
            "targetUrl": "https://www.example.com",
            "asyncEvents": [
                WebhookEventTypeAsyncEnum.ORDER_CREATED.name,
                WebhookEventTypeAsyncEnum.NOTIFY_USER.name,
            ],
        }
    }

    # when
    response = app_api_client.post_graphql(query, variables=variables)
    content = get_graphql_content(response)

    # then
    data = content["data"]["webhookCreate"]
    assert not data["webhook"]
    error = data["errors"][0]
    assert error["field"] == "asyncEvents"
    assert error["code"] == WebhookErrorCode.INVALID_NOTIFY_WITH_SUBSCRIPTION.name


FILTERABLE_SUBSCRIPTION = """
subscription {
  orderCreated(channels: [%s]) {
    order {
      id
      number
      lines {
        id
        variant {
          id
        }
      }
    }
  }
}
"""


@pytest.mark.parametrize(
    "channel_slugs",
    [
        ["channel-1", "channel-2"],
        ["channel-1"],
        [],
    ],
)
def test_webhook_create_assigns_filterable_channel_slugs(channel_slugs, app_api_client):
    # given
    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "name": "Webhook for default-channel",
            "targetUrl": "https://www.example.com",
            "query": FILTERABLE_SUBSCRIPTION
            % ",".join([f'"{slug}"' for slug in channel_slugs]),
        }
    }

    # when
    response = app_api_client.post_graphql(query, variables=variables)
    get_graphql_content(response)

    # then
    new_webhook = Webhook.objects.get()
    assert new_webhook.filterable_channel_slugs == channel_slugs
    assert new_webhook.target_url == "https://www.example.com"
    assert new_webhook.app == app_api_client.app
    events = new_webhook.events.all()
    assert len(events) == 1
    assert events[0].event_type == WebhookEventTypeAsyncEnum.ORDER_CREATED.value


@pytest.mark.parametrize(
    "channel_slugs",
    [
        ["channel-1", "channel-2"],
        ["channel-1", "channel-2", "channel-3"],
    ],
)
@patch(
    "saleor.graphql.webhook.mutations.webhook_create.MAX_FILTERABLE_CHANNEL_SLUGS_LIMIT"
)
def test_webhook_create_assigns_filterable_channel_slugs_above_max_limit(
    mocked_limit, channel_slugs, app_api_client
):
    # given
    mocked_limit.__lt__ = lambda self, compare: True

    query = WEBHOOK_CREATE
    variables = {
        "input": {
            "name": "Webhook for default-channel",
            "targetUrl": "https://www.example.com",
            "query": FILTERABLE_SUBSCRIPTION
            % ",".join([f'"{slug}"' for slug in channel_slugs]),
        }
    }

    # when
    response = app_api_client.post_graphql(query, variables=variables)
    content = get_graphql_content(response)

    # then
    assert len(content["data"]["webhookCreate"]["errors"]) == 1
    error = content["data"]["webhookCreate"]["errors"][0]
    assert error["field"] == "query"
    assert error["code"] == WebhookErrorCode.INVALID.name
