#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asynctest
import pytest

from hikari import _utils


@pytest.fixture()
def http_client(event_loop):
    from hikari_tests.test_net.test_http import ClientMock

    return ClientMock(token="foobarsecret", loop=event_loop)


@pytest.mark.asyncio
async def test_delete_channel_permission(http_client):
    http_client.request = asynctest.CoroutineMock()
    await http_client.delete_channel_permission("696969", "123456")
    http_client.request.assert_awaited_once_with(
        "delete",
        "/channels/{channel_id}/permissions/{overwrite_id}",
        channel_id="696969",
        overwrite_id="123456",
        reason=_utils.unspecified,
    )


@pytest.mark.asyncio
async def test_with_optional_reason(http_client):
    http_client.request = asynctest.CoroutineMock()
    await http_client.delete_channel_permission("696969", "123456", reason="because i can")
    args, kwargs = http_client.request.call_args
    assert kwargs["reason"] == "because i can"