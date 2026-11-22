import json

import pytest

from sessions.manager import SessionManager

from sessions.storage import (
    ConversationStorage,
    SessionNotFoundError,
    InvalidSessionDataError
)

from sessions.summary_storage import (
    SummaryStorage,
    SummaryNotFoundError
)

from sessions.summary_manager import SummaryManager


# ==========================================
# TEST FIXTURE
# ==========================================

@pytest.fixture
def summary_system(tmp_path):

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
        "conversation_storage": conversation_storage,
        "summary_storage": summary_storage,
        "session_manager": session_manager,
        "summary_manager": summary_manager,
        "session": session
    }


# ==========================================
# TEST 1: SAVE SUMMARY
# ==========================================

def test_save_summary(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    summary = manager.save_summary(
        session["session_id"],
        "The user asked about clinic opening hours."
    )

    assert summary["session_id"] == session["session_id"]

    assert summary["summary"] == (
        "The user asked about clinic opening hours."
    )


# ==========================================
# TEST 2: SUMMARY JSON FILE CREATION
# ==========================================

def test_summary_json_file_created(summary_system):

    manager = summary_system["summary_manager"]
    storage = summary_system["summary_storage"]
    session = summary_system["session"]

    manager.save_summary(
        session["session_id"],
        "The user asked about laboratory services."
    )

    file_path = (
        storage.summaries_dir
        / f"{session['session_id']}.json"
    )

    assert file_path.exists()

    saved_data = json.loads(
        file_path.read_text(encoding="utf-8")
    )

    assert saved_data["session_id"] == session["session_id"]


# ==========================================
# TEST 3: UPDATE ORIGINAL CONVERSATION
# ==========================================

def test_summary_updates_conversation(summary_system):

    manager = summary_system["summary_manager"]
    storage = summary_system["conversation_storage"]
    session = summary_system["session"]

    summary_text = "The conversation covered clinic services."

    manager.save_summary(
        session["session_id"],
        summary_text
    )

    updated_session = storage.load_session(
        session["session_id"]
    )

    assert updated_session["summary"] == summary_text


# ==========================================
# TEST 4: RETRIEVE SUMMARY
# ==========================================

def test_get_summary(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    manager.save_summary(
        session["session_id"],
        "The user requested information about appointments."
    )

    summary = manager.get_summary(
        session["session_id"]
    )

    assert summary["session_id"] == session["session_id"]

    assert "appointments" in summary["summary"]


# ==========================================
# TEST 5: LIST SUMMARIES
# ==========================================

def test_list_summaries(summary_system):

    manager = summary_system["summary_manager"]
    session_manager = summary_system["session_manager"]

    first = summary_system["session"]

    second = session_manager.create_session()

    manager.save_summary(
        first["session_id"],
        "First conversation summary."
    )

    manager.save_summary(
        second["session_id"],
        "Second conversation summary."
    )

    summaries = manager.list_summaries()

    assert len(summaries) == 2


# ==========================================
# TEST 6: COUNT SUMMARIES
# ==========================================

def test_count_summaries(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    manager.save_summary(
        session["session_id"],
        "A test summary."
    )

    assert manager.count_summaries() == 1


# ==========================================
# TEST 7: UPDATE EXISTING SUMMARY
# ==========================================

def test_update_existing_summary(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    first = manager.save_summary(
        session["session_id"],
        "Initial summary."
    )

    updated = manager.save_summary(
        session["session_id"],
        "Updated summary."
    )

    assert updated["summary"] == "Updated summary."

    assert updated["created_at"] == first["created_at"]

    assert manager.count_summaries() == 1


# ==========================================
# TEST 8: EMPTY SUMMARY REJECTION
# ==========================================

def test_empty_summary_rejected(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    with pytest.raises(ValueError):

        manager.save_summary(
            session["session_id"],
            "   "
        )


# ==========================================
# TEST 9: NON-STRING SUMMARY REJECTION
# ==========================================

def test_non_string_summary_rejected(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    with pytest.raises(ValueError):

        manager.save_summary(
            session["session_id"],
            12345
        )


# ==========================================
# TEST 10: NON-EXISTENT SESSION
# ==========================================

def test_summary_for_missing_session_rejected(summary_system):

    manager = summary_system["summary_manager"]

    with pytest.raises(SessionNotFoundError):

        manager.save_summary(
            "e6b47a2e-8bc0-4d04-b7d4-a887d39b5eb1",
            "This conversation does not exist."
        )


# ==========================================
# TEST 11: MISSING SUMMARY
# ==========================================

def test_missing_summary(summary_system):

    manager = summary_system["summary_manager"]
    session = summary_system["session"]

    with pytest.raises(SummaryNotFoundError):

        manager.get_summary(session["session_id"])


# ==========================================
# TEST 12: CORRUPTED SUMMARY JSON
# ==========================================

def test_corrupted_summary_json(summary_system):

    storage = summary_system["summary_storage"]

    session = summary_system["session"]

    file_path = (
        storage.summaries_dir
        / f"{session['session_id']}.json"
    )

    file_path.write_text(
        "{invalid summary json",
        encoding="utf-8"
    )

    with pytest.raises(InvalidSessionDataError):

        storage.load_summary(session["session_id"])


# ==========================================
# TEST 13: SKIP CORRUPTED SUMMARIES
# ==========================================

def test_list_summaries_skips_corrupted_files(
    summary_system,
    caplog
):

    manager = summary_system["summary_manager"]
    storage = summary_system["summary_storage"]
    session = summary_system["session"]

    manager.save_summary(
        session["session_id"],
        "A valid summary."
    )

    corrupt_file = (
        storage.summaries_dir / "corrupted.json"
    )

    corrupt_file.write_text(
        "{invalid json",
        encoding="utf-8"
    )

    summaries = manager.list_summaries()

    assert len(summaries) == 1

    assert "Skipping invalid summary" in caplog.text


# ==========================================
# TEST 14: INVALID SESSION ID
# ==========================================

def test_invalid_summary_session_id(summary_system):

    storage = summary_system["summary_storage"]

    with pytest.raises(InvalidSessionDataError):

        storage.load_summary("../../invalid")


# ==========================================
# TEST 15: SUMMARY MUST MATCH CONVERSATION
# ==========================================

def test_summary_and_conversation_must_match(summary_system):

    manager = summary_system["summary_manager"]
    conversation_storage = summary_system["conversation_storage"]
    summary_storage = summary_system["summary_storage"]

    session = summary_system["session"]

    manager.save_summary(
        session["session_id"],
        "Original summary."
    )

    # Change the conversation record independently
    updated_session = conversation_storage.load_session(
        session["session_id"]
    )

    updated_session["summary"] = "Different summary."

    conversation_storage.save_session(
        updated_session
    )

    assert manager.list_summaries() == []


# ==========================================
# TEST 16: ORPHAN SUMMARY
# ==========================================

def test_orphan_summary_is_not_listed(summary_system):

    manager = summary_system["summary_manager"]
    storage = summary_system["summary_storage"]

    session = summary_system["session"]

    orphan = {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "summary": "Orphan test summary."
    }

    storage.save_summary(orphan)

    # No matching summary has been saved in the session
    assert manager.list_summaries() == []