
import pytest

from sessions.manager import SessionManager

from sessions.storage import (
    ConversationStorage,
    InvalidSessionDataError
)

from sessions.summary_storage import SummaryStorage
from sessions.summary_manager import SummaryManager


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

# ==========================================
# TEST 9: FAILED CONVERSATION WRITE PRESERVES ORIGINAL FILE
# ==========================================

def test_failed_conversation_write_preserves_original_file(
    reliability_system,
    monkeypatch
):

    import sessions.storage as storage_module

    from sessions.storage import StorageError

    storage = reliability_system["conversation_storage"]
    session = reliability_system["session"]

    file_path = (
        storage.conversations_dir
        / f"{session['session_id']}.json"
    )

    original_content = file_path.read_bytes()

    session["messages"].append({
        "role": "user",
        "message": "Test atomic write failure."
    })

    def fail_replace(source, destination):
        raise OSError("Simulated file replacement failure.")

    monkeypatch.setattr(
        storage_module.os,
        "replace",
        fail_replace
    )

    with pytest.raises(StorageError):
        storage.save_session(session)

    assert file_path.read_bytes() == original_content

    assert list(storage.conversations_dir.glob("*.tmp")) == []


# ==========================================
# TEST 10: FAILED SUMMARY WRITE PRESERVES ORIGINAL FILE
# ==========================================

def test_failed_summary_write_preserves_original_file(
    reliability_system,
    monkeypatch
):

    import sessions.summary_storage as summary_module

    from sessions.storage import StorageError

    storage = reliability_system["summary_storage"]
    session = reliability_system["session"]

    summary_data = {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "summary": "Original summary."
    }

    storage.save_summary(summary_data)

    file_path = (
        storage.summaries_dir
        / f"{session['session_id']}.json"
    )

    original_content = file_path.read_bytes()

    updated_summary = dict(summary_data)
    updated_summary["summary"] = "Updated summary."

    def fail_replace(source, destination):
        raise OSError("Simulated summary replacement failure.")

    monkeypatch.setattr(
        summary_module.os,
        "replace",
        fail_replace
    )

    with pytest.raises(StorageError):
        storage.save_summary(updated_summary)

    assert file_path.read_bytes() == original_content

    assert list(storage.summaries_dir.glob("*.tmp")) == []


# ==========================================
# TEST 11: RESTORE PREVIOUS SUMMARY AFTER LINK FAILURE
# ==========================================

def test_previous_summary_restored_after_link_failure(
    reliability_system,
    monkeypatch
):

    from sessions.storage import StorageError

    manager = reliability_system["summary_manager"]
    conversation_storage = reliability_system["conversation_storage"]
    session = reliability_system["session"]

    original_text = "The original saved summary."

    manager.save_summary(
        session["session_id"],
        original_text
    )

    def fail_conversation_save(updated_session):
        raise StorageError(
            "Simulated conversation update failure."
        )

    monkeypatch.setattr(
        conversation_storage,
        "save_session",
        fail_conversation_save
    )

    with pytest.raises(StorageError):
        manager.save_summary(
            session["session_id"],
            "A replacement summary."
        )

    restored_summary = manager.get_summary(
        session["session_id"]
    )

    assert restored_summary["summary"] == original_text


# ==========================================
# TEST 12: REMOVE NEW SUMMARY AFTER LINK FAILURE
# ==========================================

def test_new_summary_removed_after_link_failure(
    reliability_system,
    monkeypatch
):

    from sessions.storage import StorageError
    from sessions.summary_storage import SummaryNotFoundError

    manager = reliability_system["summary_manager"]
    conversation_storage = reliability_system["conversation_storage"]
    summary_storage = reliability_system["summary_storage"]
    session = reliability_system["session"]

    def fail_conversation_save(updated_session):
        raise StorageError(
            "Simulated conversation update failure."
        )

    monkeypatch.setattr(
        conversation_storage,
        "save_session",
        fail_conversation_save
    )

    with pytest.raises(StorageError):
        manager.save_summary(
            session["session_id"],
            "A summary that should not remain saved."
        )

    with pytest.raises(SummaryNotFoundError):
        summary_storage.load_summary(
            session["session_id"]
        )

# ==========================================
# TEST 13: LOGGING FALLBACK WHEN FILE LOGGING FAILS
# ==========================================

def test_logging_falls_back_when_file_handler_fails(
    tmp_path,
    monkeypatch
):

    import logging

    import core.logging_config as logging_module

    logger = logging.getLogger("clinic_faq")

    original_handlers = logger.handlers[:]
    original_level = logger.level
    original_propagate = logger.propagate

    try:

        logger.handlers.clear()

        def fail_file_handler(*args, **kwargs):
            raise PermissionError(
                "Simulated log file permission failure."
            )

        monkeypatch.setattr(
            logging_module,
            "RotatingFileHandler",
            fail_file_handler
        )

        configured_logger = logging_module.configure_logging()

        assert configured_logger is logger

        assert any(
            isinstance(handler, logging.StreamHandler)
            for handler in configured_logger.handlers
        )

        assert configured_logger.propagate is False

    finally:

        logger.handlers.clear()

        logger.handlers.extend(original_handlers)

        logger.setLevel(original_level)
        logger.propagate = original_propagate

def test_logging_falls_back_when_log_directory_creation_fails(
    monkeypatch
):
    import logging
    import core.logging_config as logging_module

    logger = logging.getLogger("clinic_faq")

    original_handlers = logger.handlers[:]
    original_level = logger.level
    original_propagate = logger.propagate

    try:
        logger.handlers.clear()

        def fail_directory_creation(*args, **kwargs):
            raise PermissionError(
                "Simulated log directory permission failure."
            )

        monkeypatch.setattr(
            logging_module.Path,
            "mkdir",
            fail_directory_creation
        )

        configured_logger = logging_module.configure_logging()

        assert configured_logger is logger

        assert any(
            type(handler) is logging.StreamHandler
            for handler in configured_logger.handlers
        )

        assert configured_logger.propagate is False

    finally:
        logger.handlers.clear()
        logger.handlers.extend(original_handlers)
        logger.setLevel(original_level)
        logger.propagate = original_propagate
