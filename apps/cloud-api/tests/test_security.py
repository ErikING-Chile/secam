from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app import security


@pytest.mark.asyncio
async def test_get_current_user_for_media_prefers_bearer_token_over_query_token():
    db = Mock()
    credentials = SimpleNamespace(credentials="bearer-token")
    expected_user = object()

    with patch.object(security, "_get_user_from_token", return_value=expected_user) as get_user:
        user = await security.get_current_user_for_media(
            token="query-token",
            credentials=credentials,
            db=db,
        )

    assert user is expected_user
    get_user.assert_called_once_with("bearer-token", db)


@pytest.mark.asyncio
async def test_get_current_user_for_media_falls_back_to_query_token():
    db = Mock()
    expected_user = object()

    with patch.object(security, "_get_user_from_token", return_value=expected_user) as get_user:
        user = await security.get_current_user_for_media(
            token="query-token",
            credentials=None,
            db=db,
        )

    assert user is expected_user
    get_user.assert_called_once_with("query-token", db)
