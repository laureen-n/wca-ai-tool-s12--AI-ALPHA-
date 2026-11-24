
import pytest

from sessions.manager import SessionManager
from sessions.storage import (
    ConversationStorage,
    SessionNotFoundError,
    StorageError
)
from sessions.summary_storage import SummaryStorage
from sessions.summary_manager import SummaryManager


@pytest.fixture
def deletion_system(tmp_path):

    conversation_storage = ConversationStorage(
        tmp_path / "conversations"
    )

    summary_storage = SummaryStorage(
        tmp_path / "summaries"
    )

    session_manager = SessionManager(
        storage=conversation_storage
    )

    summary_manager = SummaryManager(
        conversation_storage=conversation_storage,
        summary_storage=summary_storage
    )

    session = session_manager.create_session()

    return {
        "session_manager": session_manager,
        "summary_manager": summary_manager,
        "conversation_storage": conversation_storage,
        "summary_storage": summary_storage,
        "session": session
    }


def test_delete_conversation_without_summary(deletion_system):

    manager = deletion_system["session_manager"]
    summary_manager = deletion_system["summary_manager"]
    session = deletion_system["session"]

    result = manager.delete_session(
        session["session_id"],
        summary_manager
    )

    assert result is True

    with pytest.raises(SessionNotFoundError):
        manager.open_session(session["session_id"])


def test_delete_conversation_and_summary(deletion_system):

    manager = deletion_system["session_manager"]
    summary_manager = deletion_system["summary_manager"]
    summary_storage = deletion_system["summary_storage"]
    session = deletion_system["session"]

    summary_manager.save_summary(
        session["session_id"],
        "The user asked about clinic services."
    )

    result = manager.delete_session(
        session["session_id"],
        summary_manager
    )

    assert result is True

    with pytest.raises(SessionNotFoundError):
        manager.open_session(session["session_id"])

    from sessions.summary_storage import SummaryNotFoundError

    with pytest.raises(SummaryNotFoundError):
        summary_storage.load_summary(session["session_id"])


def test_delete_missing_conversation(deletion_system):

    manager = deletion_system["session_manager"]
    summary_manager = deletion_system["summary_manager"]

    with pytest.raises(SessionNotFoundError):

        manager.delete_session(
            "e6b47a2e-8bc0-4d04-b7d4-a887d39b5eb1",
            summary_manager
        )


def test_delete_requires_summary_manager(deletion_system):

    manager = deletion_system["session_manager"]
    session = deletion_system["session"]

    with pytest.raises(ValueError):

        manager.delete_session(
            session["session_id"],
            None
        )


def test_summary_is_restored_if_conversation_deletion_fails(
    deletion_system,
    monkeypatch
):

    manager = deletion_system["session_manager"]
    summary_manager = deletion_system["summary_manager"]
    summary_storage = deletion_system["summary_storage"]
    session = deletion_system["session"]

    summary_text = "The user asked about appointments."

    summary_manager.save_summary(
        session["session_id"],
        summary_text
    )

    def simulate_delete_failure(session_id):

        raise StorageError(
            "Simulated conversation deletion failure."
        )

    monkeypatch.setattr(
        manager.storage,
        "delete_session",
        simulate_delete_failure
    )

    with pytest.raises(StorageError):

        manager.delete_session(
            session["session_id"],
            summary_manager
        )

    # The conversation must remain.
    reopened = manager.open_session(
        session["session_id"]
    )

    assert reopened["summary"] == summary_text

    # Its summary must also be restored.
    restored_summary = summary_storage.load_summary(
        session["session_id"]
    )

    assert restored_summary["summary"] == summary_text
