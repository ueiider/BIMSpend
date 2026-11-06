import pytest
from bimspend.identity import Actor, Role, current_auth
from bimspend.models import TimeEntry, TimeEntryState
from bimspend.review import submit_entry, approve_entry, reject_entry, bill_entry, reset_to_pending, edit_entry


def _set_actor(user_id: str, role: Role, company_id: str | None = None):
    current_auth.set_actor(Actor(id=user_id, role=role, company_id=company_id))


def entry():
    return TimeEntry("e", "a", "p", "designer_01", 60)


def test_only_owner_designer_can_submit():
    sample = entry()
    # Non-owner designer cannot submit
    for user in ("designer_02", "manager_01", "unknown"):
        _set_actor(user, Role.DESIGNER)
        with pytest.raises(PermissionError):
            submit_entry(sample)
        assert sample.state == TimeEntryState.PENDING_REVIEW
    # Owner designer can submit
    _set_actor("designer_01", Role.DESIGNER)
    submit_entry(sample)
    assert sample.state == TimeEntryState.SUBMITTED


def test_only_manager_can_approve_reject_and_bill():
    current_auth.clear()
    sample = entry()
    submit_entry(sample, "designer_01")
    assert sample.state == TimeEntryState.SUBMITTED
    # Manager rejects
    reject_entry(sample, "manager_01")
    assert sample.state == TimeEntryState.REJECTED
    # Designer owner can reset
    _set_actor("designer_01", Role.DESIGNER)
    reset_to_pending(sample)
    assert sample.state == TimeEntryState.PENDING_REVIEW
    # Designer owner can submit again
    submit_entry(sample)
    assert sample.state == TimeEntryState.SUBMITTED
    # Manager can approve
    _set_actor("manager_01", Role.MANAGER)
    approve_entry(sample)
    assert sample.state == TimeEntryState.APPROVED
    # Designer cannot bill
    _set_actor("designer_01", Role.DESIGNER)
    with pytest.raises(PermissionError):
        bill_entry(sample, 45)
    assert sample.billed_minutes == 0
    # Manager can bill
    _set_actor("manager_01", Role.MANAGER)
    bill_entry(sample, 45)
    assert sample.billed_minutes == 45


def test_rejection_and_reset_are_owned_by_correct_actors():
    sample = entry()
    # Non-owner designer cannot reject
    with pytest.raises(PermissionError):
        _set_actor("designer_02", Role.DESIGNER)
        reject_entry(sample)
    # Owner designer can reject pending
    _set_actor("designer_01", Role.DESIGNER)
    reject_entry(sample)
    assert sample.state == TimeEntryState.REJECTED
    # Manager cannot reset
    _set_actor("manager_01", Role.MANAGER)
    with pytest.raises(PermissionError):
        reset_to_pending(sample)
    assert sample.state == TimeEntryState.REJECTED
    # Designer owner can reset again
    _set_actor("designer_01", Role.DESIGNER)
    reset_to_pending(sample)
    assert sample.state == TimeEntryState.PENDING_REVIEW