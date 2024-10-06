import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytz
from freezegun import freeze_time

from ......plugins.base_plugin import ExternalAccessTokens
from .....tests.utils import get_graphql_content

MUTATION_EXTERNAL_REFRESH = """
    mutation externalRefresh($pluginId: String!, $input: JSONString!){
        externalRefresh(pluginId: $pluginId, input: $input){
            token
            refreshToken
            csrfToken
            user{
                email
            }
            errors{
                field
                message
            }
        }
}
"""


def test_external_refresh_plugin_not_active(api_client, customer_user):
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}
    response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)
    content = get_graphql_content(response)
    data = content["data"]["externalRefresh"]
    assert data["token"] is None
    assert data["refreshToken"] is None
    assert data["csrfToken"] is None
    assert data["user"] is None


@freeze_time("2018-05-31 12:00:00")
@patch("saleor.core.middleware.jwt_decode_with_exception_handler")
def test_external_refresh(
    mock_refresh_token_middleware, api_client, customer_user, monkeypatch, rf
):
    expected_token = "token1"
    expected_refresh_token = "refresh2"
    expected_csrf_token = "csrf3"
    mocked_plugin_fun = Mock()
    expected_return = ExternalAccessTokens(
        token=expected_token,
        refresh_token=expected_refresh_token,
        csrf_token=expected_csrf_token,
        user=customer_user,
    )
    mocked_plugin_fun.return_value = expected_return
    monkeypatch.setattr(
        "saleor.plugins.manager.PluginsManager.external_refresh", mocked_plugin_fun
    )
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}
    response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)
    content = get_graphql_content(response)
    data = content["data"]["externalRefresh"]
    assert data["token"] == expected_token
    assert data["refreshToken"] == expected_refresh_token
    assert data["csrfToken"] == expected_csrf_token
    assert data["user"]["email"] == customer_user.email
    assert customer_user.last_login
    last_login = customer_user.last_login.strftime("%Y-%m-%d %H:%M:%S")
    assert last_login == "2018-05-31 12:00:00"
    assert mocked_plugin_fun.called
    assert mock_refresh_token_middleware.called


@freeze_time("2018-05-31 12:00:00")
@patch("saleor.core.middleware.jwt_decode_with_exception_handler")
def test_external_refresh_do_not_update_last_login_when_in_threshold(
    mock_refresh_token_middleware, api_client, customer_user, monkeypatch, rf, settings
):
    # given
    expected_token = "token1"
    expected_refresh_token = "refresh2"
    expected_csrf_token = "csrf3"
    mocked_plugin_fun = Mock()
    expected_return = ExternalAccessTokens(
        token=expected_token,
        refresh_token=expected_refresh_token,
        csrf_token=expected_csrf_token,
        user=customer_user,
    )
    mocked_plugin_fun.return_value = expected_return
    monkeypatch.setattr(
        "saleor.plugins.manager.PluginsManager.external_refresh", mocked_plugin_fun
    )
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}

    customer_user.last_login = datetime.now(tz=pytz.UTC)
    customer_user.save()
    expected_last_login = customer_user.last_login
    expected_updated_at = customer_user.updated_at

    time_in_threshold = datetime.now(tz=pytz.UTC) + timedelta(
        seconds=settings.TOKEN_UPDATE_LAST_LOGIN_THRESHOLD - 1
    )

    # when
    with freeze_time(time_in_threshold):
        response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)

    # then
    get_graphql_content(response)
    customer_user.refresh_from_db()
    assert customer_user.updated_at == expected_updated_at
    assert customer_user.last_login == expected_last_login
    assert mock_refresh_token_middleware.called


@freeze_time("2018-05-31 12:00:00")
@patch("saleor.core.middleware.jwt_decode_with_exception_handler")
def test_external_refresh_do_update_last_login_when_out_of_threshold(
    mock_refresh_token_middleware, api_client, customer_user, monkeypatch, rf, settings
):
    # given
    expected_token = "token1"
    expected_refresh_token = "refresh2"
    expected_csrf_token = "csrf3"
    mocked_plugin_fun = Mock()
    expected_return = ExternalAccessTokens(
        token=expected_token,
        refresh_token=expected_refresh_token,
        csrf_token=expected_csrf_token,
        user=customer_user,
    )
    mocked_plugin_fun.return_value = expected_return
    monkeypatch.setattr(
        "saleor.plugins.manager.PluginsManager.external_refresh", mocked_plugin_fun
    )
    variables = {"pluginId": "pluginId1", "input": json.dumps({"refreshToken": "ABCD"})}

    customer_user.last_login = datetime.now(tz=pytz.UTC)
    customer_user.save()
    previous_last_login = customer_user.last_login
    previous_updated_at = customer_user.updated_at

    time_out_of_threshold = datetime.now(tz=pytz.UTC) + timedelta(
        seconds=settings.TOKEN_UPDATE_LAST_LOGIN_THRESHOLD + 1
    )

    # when
    with freeze_time(time_out_of_threshold):
        response = api_client.post_graphql(MUTATION_EXTERNAL_REFRESH, variables)

    # then
    get_graphql_content(response)
    customer_user.refresh_from_db()
    assert customer_user.updated_at != previous_updated_at
    assert customer_user.last_login != previous_last_login
    assert customer_user.updated_at == time_out_of_threshold
    assert customer_user.last_login == time_out_of_threshold
    assert mock_refresh_token_middleware.called
