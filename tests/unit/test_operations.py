from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest

from keitaro_wrapper.application.common.commands import Commands
from keitaro_wrapper.common.identity import Identity
from keitaro_wrapper.domain.common.errors import DomainError

NOW = datetime(2026, 11, 18, tzinfo=UTC)
LATER = NOW + timedelta(minutes=1)


def operation(kind="push", reserves=True):
    return Commands.build(Identity.new(), kind, Identity.new(), {}, reserves=reserves, now=NOW)


@pytest.mark.parametrize("status", ["succeeded", "failed", "conflict", "unknown", "manual_review"])
def test_transition_cannot_restart_or_rewrite_a_finished_attempt(status):
    command = operation()
    command.transition(status, at=LATER)
    before = asdict(command)
    with pytest.raises(DomainError, match="переход"):
        command.transition("running", at=LATER)
    with pytest.raises(DomainError):
        command.checkpoint(stage="publish", at=LATER)
    assert asdict(command) == before


def test_unknown_write_cannot_be_resumed_without_reconciliation():
    command = operation()
    command.transition("unknown", at=LATER)
    before = asdict(command)
    with pytest.raises(DomainError):
        command.begin_control("resume", at=LATER)
    assert asdict(command) == before
    command.begin_control("reconcile", at=LATER)
    assert command.status == "running"
    command.transition("succeeded", at=LATER)
    assert not command.allows_control("resume")


def test_rejected_create_can_resume_and_only_create_can_be_partial():
    command = operation("create")
    command.transition("partial", at=LATER)
    command.begin_control("resume", at=LATER)
    assert command.status == "running"
    other = operation()
    with pytest.raises(DomainError):
        other.transition("partial", at=LATER)
    assert other.status == "running"
    assert other.revision == 0


def test_control_receipt_cannot_reserve_unknown_external_outcome():
    command = operation("control", reserves=False)
    with pytest.raises(DomainError):
        command.transition("unknown", at=LATER)
    command.transition("failed", at=LATER)
    assert not command.allows_control("resume")


def test_domain_uses_the_supplied_time_for_creation_and_changes():
    command = operation()
    assert command.created_at == command.updated_at == NOW
    command.checkpoint(stage="publish", at=LATER)
    assert command.updated_at == LATER
    command.transition("succeeded", at=LATER + timedelta(seconds=1))
    assert command.created_at == NOW
    assert command.updated_at == LATER + timedelta(seconds=1)


def test_invalid_status_leaves_operation_untouched():
    command = operation()
    before = asdict(command)
    with pytest.raises(DomainError):
        command.transition("typo", at=LATER)
    assert asdict(command) == before
