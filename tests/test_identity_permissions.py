import pytest
from bimspend.models import TimeEntry, TimeEntryState
from bimspend.review import submit_entry, approve_entry, reject_entry, bill_entry, reset_to_pending


def entry():
    return TimeEntry("e", "a", "p", "designer_01", 60)


def test_only_owner_designer_can_submit():
    sample = entry()
    for user in ("designer_02", "manager_01", "unknown"):
        with pytest.raises(PermissionError):
            submit_entry(sample, user)
        assert sample.state == TimeEntryState.PENDING_REVIEW
    submit_entry(sample, "designer_01")
    assert sample.state == TimeEntryState.SUBMITTED


def test_only_manager_can_approve_reject_and_bill():
    sample = entry()
    submit_entry(sample, "designer_01")
    for user in ("designer_01", "unknown"):
        with pytest.raises(PermissionError):
            approve_entry(sample, user)
        with pytest.raises(PermissionError):
            reject_entry(sample, user)
        assert sample.state == TimeEntryState.SUBMITTED
    approve_entry(sample, "manager_01")
    for user in ("designer_01", "unknown"):
        with pytest.raises(PermissionError):
            bill_entry(sample, 45, user)
        assert sample.billed_minutes == 0
    bill_entry(sample, 45, "manager_01")
    assert sample.billed_minutes == 45


def test_rejection_and_reset_are_owned_by_correct_actors():
    sample = entry()
    with pytest.raises(PermissionError):
        reject_entry(sample, "designer_02")
    reject_entry(sample, "designer_01")
    with pytest.raises(PermissionError):
        reset_to_pending(sample, "manager_01")
    reset_to_pending(sample, "designer_01")
    submit_entry(sample, "designer_01")
    reject_entry(sample, "manager_demo")
    assert sample.state == TimeEntryState.REJECTED
