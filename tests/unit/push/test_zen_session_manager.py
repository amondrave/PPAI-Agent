"""Unit tests for ZenSessionManager (DP-SCHED-04)."""

from datetime import datetime, timezone

import pytest

from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences


class TestActivateDeactivate:
    def test_activate_creates_session(self):
        mgr = ZenSessionManager()
        session = mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        assert session.user_id == "u1"
        assert session.nudges_sent == 0
        assert session.max_nudges == 10

    def test_activate_idempotent(self):
        mgr = ZenSessionManager()
        s1 = mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        s2 = mgr.activate("u1", zen_max_nudges=20, zen_interval_minutes=5)
        assert s1 is s2  # returns existing, does not overwrite

    def test_deactivate_returns_session(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        session = mgr.deactivate("u1")
        assert session is not None
        assert session.user_id == "u1"

    def test_deactivate_nonexistent_returns_none(self):
        mgr = ZenSessionManager()
        assert mgr.deactivate("u1") is None

    def test_get_active_session(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        assert mgr.get("u1") is not None

    def test_get_after_deactivate_returns_none(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        mgr.deactivate("u1")
        assert mgr.get("u1") is None


class TestRecordNudge:
    def test_record_increments(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        result = mgr.record_nudge("u1")
        assert result is True
        assert mgr.get("u1").nudges_sent == 1

    def test_record_returns_false_at_cap(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=2, zen_interval_minutes=15)
        mgr.record_nudge("u1")  # 1
        result = mgr.record_nudge("u1")  # 2 = cap
        assert result is False

    def test_record_nonexistent_returns_false(self):
        mgr = ZenSessionManager()
        assert mgr.record_nudge("u1") is False


class TestReconstructFromPrefs:
    def test_reconstructs_active_users(self):
        mgr = ZenSessionManager()
        prefs = [
            UserNudgePreferences(user_id="u1", zen_active=True, zen_max_nudges=5, zen_interval_minutes=10),
            UserNudgePreferences(user_id="u2", zen_active=False),
            UserNudgePreferences(user_id="u3", zen_active=True, zen_max_nudges=8, zen_interval_minutes=20),
        ]
        mgr.reconstruct_from_prefs(prefs)
        assert mgr.get("u1") is not None
        assert mgr.get("u2") is None
        assert mgr.get("u3") is not None
        assert mgr.get("u1").nudges_sent == 0  # reset on reconstruct


class TestGetMinInterval:
    def test_no_sessions_returns_none(self):
        mgr = ZenSessionManager()
        assert mgr.get_min_interval() is None

    def test_single_session(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=10)
        assert mgr.get_min_interval() == 10

    def test_multiple_sessions_returns_min(self):
        mgr = ZenSessionManager()
        mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
        mgr.activate("u2", zen_max_nudges=10, zen_interval_minutes=5)
        mgr.activate("u3", zen_max_nudges=10, zen_interval_minutes=10)
        assert mgr.get_min_interval() == 5
