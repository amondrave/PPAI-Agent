from ppai.capture.domain.value_objects import TaskStatus, ACTIVE_STATUSES


class TestTaskStatus:
    def test_all_statuses_exist(self):
        expected = {"captured", "pending", "prioritized", "nudged", "done", "snoozed", "clarifying", "needs_clarification"}
        actual = {s.value for s in TaskStatus}
        assert actual == expected

    def test_status_is_string(self):
        assert TaskStatus.CAPTURED == "captured"
        assert str(TaskStatus.PENDING) == "pending"

    def test_active_statuses_exclude_done(self):
        assert TaskStatus.DONE not in ACTIVE_STATUSES

    def test_active_statuses_count(self):
        assert len(ACTIVE_STATUSES) == 6

    def test_all_active_statuses_are_valid(self):
        for status in ACTIVE_STATUSES:
            assert status in TaskStatus
