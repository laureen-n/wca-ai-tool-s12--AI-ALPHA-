import json

import pytest

from sessions.manager import SessionManager

from sessions.storage import (
    ConversationStorage,
    SessionNotFoundError,
    InvalidSessionDataError
)


# ==========================================
# TEST FIXTURE
# ==========================================

@pytest.fixture
def session_manager(tmp_path):

    conversation_directory = tmp_path / "conversations"

    storage = ConversationStorage(
        conversations_dir=conversation_directory
    )

    return SessionManager(storage=storage)


# ==========================================
# TEST 1: CREATE SESSION
# ==========================================

def test_create_session(session_manager):

    session = session_manager.create_session()

    assert session["session_id"]

    assert session["created_at"]

    assert session["updated_at"]

    assert session["messages"] == []

    assert session["summary"] is None


# ==========================================
# TEST 2: UUID GENERATION
# ==========================================

def test_sessions_have_unique_ids(session_manager):

    first_session = session_manager.create_session()

    second_session = session_manager.create_session()

    assert first_session["session_id"] != second_session["session_id"]


# ==========================================
# TEST 3: SESSION AUTOMATICALLY SAVED
# ==========================================

def test_create_session_saves_json(session_manager):

    session = session_manager.create_session()

    session_file = (
        session_manager.storage.conversations_dir
        / f"{session['session_id']}.json"
    )

    assert session_file.exists()

    saved_data = json.loads(
        session_file.read_text(encoding="utf-8")
    )

    assert saved_data["session_id"] == session["session_id"]


# ==========================================
# TEST 4: OPEN EXISTING SESSION
# ==========================================

def test_open_existing_session(session_manager):

    created = session_manager.create_session()

    opened = session_manager.open_session(
        created["session_id"]
    )

    assert opened["session_id"] == created["session_id"]


# ==========================================
# TEST 5: ADD USER MESSAGE
# ==========================================

def test_add_user_message(session_manager):

    session = session_manager.create_session()

    updated = session_manager.add_message(
        session["session_id"],
        "user",
        "What are your clinic opening hours?"
    )

    assert len(updated["messages"]) == 1

    assert updated["messages"][0]["role"] == "user"

    assert (
        updated["messages"][0]["message"]
        == "What are your clinic opening hours?"
    )


# ==========================================
# TEST 6: ADD ASSISTANT MESSAGE
# ==========================================

def test_add_assistant_message(session_manager):

    session = session_manager.create_session()

    session_manager.add_message(
        session["session_id"],
        "user",
        "Do you offer dental services?"
    )

    updated = session_manager.add_message(
        session["session_id"],
        "assistant",
        "Please contact reception for information about dental services."
    )

    assert len(updated["messages"]) == 2

    assert updated["messages"][1]["role"] == "assistant"


# ==========================================
# TEST 7: MESSAGE PERSISTENCE
# ==========================================

def test_messages_survive_reopening(session_manager):

    session = session_manager.create_session()

    session_manager.add_message(
        session["session_id"],
        "user",
        "Do you offer laboratory services?"
    )

    reopened = session_manager.open_session(
        session["session_id"]
    )

    assert len(reopened["messages"]) == 1

    assert (
        reopened["messages"][0]["message"]
        == "Do you offer laboratory services?"
    )


# ==========================================
# TEST 8: EMPTY MESSAGE REJECTION
# ==========================================

def test_empty_message_rejected(session_manager):

    session = session_manager.create_session()

    with pytest.raises(ValueError):

        session_manager.add_message(
            session["session_id"],
            "user",
            "   "
        )


# ==========================================
# TEST 9: INVALID ROLE REJECTION
# ==========================================

def test_invalid_role_rejected(session_manager):

    session = session_manager.create_session()

    with pytest.raises(ValueError):

        session_manager.add_message(
            session["session_id"],
            "admin",
            "Testing invalid role"
        )


# ==========================================
# TEST 10: MISSING SESSION HANDLING
# ==========================================

def test_missing_session(session_manager):

    with pytest.raises(SessionNotFoundError):

        session_manager.open_session(
            "e6b47a2e-8bc0-4d04-b7d4-a887d39b5eb1"
        )


# ==========================================
# TEST 11: INVALID UUID HANDLING
# ==========================================

def test_invalid_session_id(session_manager):

    with pytest.raises(InvalidSessionDataError):

        session_manager.open_session(
            "../../invalid"
        )


# ==========================================
# TEST 12: CORRUPTED JSON HANDLING
# ==========================================

def test_corrupted_json_handling(session_manager):

    session_id = "e6b47a2e-8bc0-4d04-b7d4-a887d39b5eb1"

    file_path = (
        session_manager.storage.conversations_dir
        / f"{session_id}.json"
    )

    file_path.write_text(
        "{invalid json content",
        encoding="utf-8"
    )

    with pytest.raises(InvalidSessionDataError):

        session_manager.open_session(session_id)


# ==========================================
# TEST 13: LIST ALL SESSIONS
# ==========================================

def test_list_sessions(session_manager):

    session_manager.create_session()

    session_manager.create_session()

    sessions = session_manager.list_sessions()

    assert len(sessions) == 2


# ==========================================
# TEST 14: COUNT SESSIONS
# ==========================================

def test_count_sessions(session_manager):

    session_manager.create_session()

    session_manager.create_session()

    assert session_manager.count_sessions() == 2


# ==========================================
# TEST 15: SKIP CORRUPTED FILES WHEN LISTING
# ==========================================

def test_list_sessions_skips_corrupted_files(session_manager, caplog):

    session_manager.create_session()

    corrupt_file = (
        session_manager.storage.conversations_dir
        / "corrupted.json"
    )

    corrupt_file.write_text(
        "{not valid json",
        encoding="utf-8"
    )

    sessions = session_manager.list_sessions()

    assert len(sessions) == 1

    assert "Skipping invalid conversation file" in caplog.text