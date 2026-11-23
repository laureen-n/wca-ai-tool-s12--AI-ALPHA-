
import pytest

from sessions.manager import SessionManager

from sessions.storage import (
    ConversationStorage,
    InvalidSessionDataError
)

from sessions.summary_storage import SummaryStorage


# ==========================================
# TEST FIXTURE
# ==========================================

@pytest.fixture
def reliability_system(tmp_path):

    conversation_storage = ConversationStorage(
        tmp_path / "conversations"
    )

    summary_storage = SummaryStorage(
        tmp_path / "summaries"
    )

    session_manager = SessionManager(
        storage=conversation_storage
    )

    session = session_manager.create_session()

    return {
        "conversation_storage": conversation_storage,
        "summary_storage": summary_storage,
        "session_manager": session_manager,
        "session": session
    }


# ==========================================
# TEST 1: NORMALIZE SESSION UUID
# ==========================================

def test_session_uuid_normalized(reliability_system):

    storage = reliability_system["conversation_storage"]

    session = reliability_system["session"]

    original_id = session["session_id"]

    session["session_id"] = original_id.upper()

    file_path = storage.save_session(session)

    loaded = storage.load_session(original_id.upper())

    assert file_path.stem == original_id

    assert loaded["session_id"] == original_id


# ==========================================
# TEST 2: REJECT INVALID MESSAGE STRUCTURE
# ==========================================

def test_invalid_message_structure_rejected(reliability_system):

    storage = reliability_system["conversation_storage"]

    session = reliability_system["session"]

    session["messages"] = [
        {
            "role": "user",
            "message": "   "
        }
    ]

    with pytest.raises(InvalidSessionDataError):

        storage.save_session(session)


# ==========================================
# TEST 3: REJECT INVALID SESSION TIMESTAMP
# ==========================================

def test_invalid_session_timestamp_rejected(reliability_system):

    storage = reliability_system["conversation_storage"]

    session = reliability_system["session"]

    session["created_at"] = "invalid-timestamp"

    with pytest.raises(InvalidSessionDataError):

        storage.save_session(session)


# ==========================================
# TEST 4: HANDLE INVALID UTF-8 CONVERSATION
# ==========================================

def test_invalid_utf8_conversation(reliability_system):

    storage = reliability_system["conversation_storage"]

    session = reliability_system["session"]

    session_file = (
        storage.conversations_dir
        / f"{session['session_id']}.json"
    )

    session_file.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(InvalidSessionDataError):

        storage.load_session(session["session_id"])


# ==========================================
# TEST 5: NORMALIZE SUMMARY UUID
# ==========================================

def test_summary_uuid_normalized(reliability_system):

    storage = reliability_system["summary_storage"]

    session = reliability_system["session"]

    session_id = session["session_id"]

    summary_data = {
        "session_id": session_id.upper(),
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "summary": "A reliability test summary."
    }

    file_path = storage.save_summary(summary_data)

    loaded = storage.load_summary(session_id.upper())

    assert file_path.stem == session_id

    assert loaded["session_id"] == session_id


# ==========================================
# TEST 6: REJECT EMPTY SUMMARY
# ==========================================

def test_empty_summary_storage_rejected(reliability_system):

    storage = reliability_system["summary_storage"]

    session = reliability_system["session"]

    summary_data = {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "summary": "   "
    }

    with pytest.raises(InvalidSessionDataError):

        storage.save_summary(summary_data)


# ==========================================
# TEST 7: REJECT INVALID SUMMARY TIMESTAMP
# ==========================================

def test_invalid_summary_timestamp_rejected(reliability_system):

    storage = reliability_system["summary_storage"]

    session = reliability_system["session"]

    summary_data = {
        "session_id": session["session_id"],
        "created_at": "invalid-timestamp",
        "updated_at": session["updated_at"],
        "summary": "A test summary."
    }

    with pytest.raises(InvalidSessionDataError):

        storage.save_summary(summary_data)


# ==========================================
# TEST 8: HANDLE INVALID UTF-8 SUMMARY
# ==========================================

def test_invalid_utf8_summary(reliability_system):

    storage = reliability_system["summary_storage"]

    session = reliability_system["session"]

    summary_file = (
        storage.summaries_dir
        / f"{session['session_id']}.json"
    )

    summary_file.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(InvalidSessionDataError):

        storage.load_summary(session["session_id"])
