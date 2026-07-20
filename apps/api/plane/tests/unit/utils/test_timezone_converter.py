# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# PP-85 regression: user_timezone_converter used to crash with an
# AttributeError when called with `queryset=None` (e.g. IssueViewSet.create
# re-fetching a just-created row that didn't match the viewset's filtered
# queryset -- the exact case for IwEpicViewSet before the epic type existed).

from datetime import datetime, timezone as dt_timezone

import pytest

from plane.utils.timezone_converter import user_timezone_converter


@pytest.mark.unit
class TestUserTimezoneConverterNoneHandling:
    """Test that user_timezone_converter degrades gracefully on a None input"""

    def test_none_queryset_returns_none(self):
        """Calling with queryset=None must return None, not raise"""
        result = user_timezone_converter(None, ["created_at", "updated_at"], "UTC")
        assert result is None

    def test_none_queryset_returns_none_with_empty_fields(self):
        """None handling should not depend on the datetime_fields list contents"""
        result = user_timezone_converter(None, [], "UTC")
        assert result is None

    def test_none_queryset_returns_none_with_non_utc_timezone(self):
        """None handling should short-circuit before the pytz timezone lookup"""
        result = user_timezone_converter(None, ["created_at"], "Asia/Kolkata")
        assert result is None


@pytest.mark.unit
class TestUserTimezoneConverterExistingBehaviour:
    """Guard the pre-existing (non-None) behaviour while touching this function"""

    def test_dict_queryset_converts_datetime_fields(self):
        item = {
            "id": 1,
            "created_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc),
        }
        result = user_timezone_converter(item, ["created_at"], "UTC")
        assert result["created_at"].tzinfo is not None

    def test_list_queryset_converts_datetime_fields(self):
        items = [
            {"id": 1, "created_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=dt_timezone.utc)},
            {"id": 2, "created_at": datetime(2026, 1, 2, 12, 0, 0, tzinfo=dt_timezone.utc)},
        ]
        result = user_timezone_converter(items, ["created_at"], "UTC")
        assert len(result) == 2
        assert all(r["created_at"].tzinfo is not None for r in result)
