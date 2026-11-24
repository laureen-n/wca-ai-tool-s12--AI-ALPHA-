
import logging

from datetime import datetime, timezone
from uuid import uuid4

import memory as conversation_memory

from sessions.storage import (
    ConversationStorage,
    StorageError
)

from sessions.summary_storage import SummaryNotFoundError


logger = logging.getLogger("clinic_faq.sessions")


class SessionManager:
    """
    Manages clinic FAQ conversation sessions.

    Integrates with Role 2's existing memory.py.
    """

    def __init__(self, storage=None):

        self.storage = storage or ConversationStorage()

    # ======================================
    # CURRENT TIMESTAMP
    # ======================================

    @staticmethod
    def _current_timestamp():

        return datetime.now(
            timezone.utc
        ).isoformat()

    # ======================================
    # CREATE SESSION
    # ======================================

    def create_session(self):

        timestamp = self._current_timestamp()

        session = {
            "session_id": str(uuid4()),
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": conversation_memory.create_history(),
            "summary": None
        }

        self.storage.save_session(session)

        logger.info("New conversation created.")

        return session

    # ======================================
    # OPEN SESSION
    # ======================================

    def open_session(self, session_id):

        return self.storage.load_session(session_id)

    # ======================================
    # ADD MESSAGE
    # ======================================

    def add_message(self, session_id, role, message):
        """Add a message and automatically save the conversation."""

        if role not in ("user", "assistant"):

            raise ValueError(
                "Role must be 'user' or 'assistant'."
            )

        if not isinstance(message, str) or not message.strip():

            raise ValueError(
                "Message cannot be empty."
            )

        session = self.open_session(session_id)

        conversation_memory.add_to_history(
            session["messages"],
            role,
            message.strip()
        )

        session["updated_at"] = self._current_timestamp()

        self.storage.save_session(session)

        logger.info("Conversation message saved.")

        return session

    # ======================================
    # GET HISTORY
    # ======================================

    def get_session_history(self, session_id):

        session = self.open_session(session_id)

        return conversation_memory.get_history(
            session["messages"]
        )

    # ======================================
    # LIST SESSIONS
    # ======================================

    def list_sessions(self):

        return self.storage.list_sessions()

    # ======================================
    # COUNT SESSIONS
    # ======================================

    def count_sessions(self):

        return len(self.list_sessions())

    # ======================================
    # DELETE SESSION AND LINKED SUMMARY
    # ======================================

    def delete_session(self, session_id, summary_manager):
        """
        Delete a conversation and its associated summary.

        The summary is removed first. If conversation deletion
        fails, the summary is restored where possible.
        """

        if summary_manager is None:

            raise ValueError(
                "A summary manager is required for safe deletion."
            )

        # Confirm the conversation exists and is valid.
        session = self.open_session(session_id)

        normalized_id = session["session_id"]

        summary_storage = summary_manager.summary_storage

        # Preserve an existing summary so it can be restored
        # if deleting the conversation fails.
        try:

            previous_summary = summary_storage.load_summary(
                normalized_id
            )

        except SummaryNotFoundError:

            previous_summary = None

        # Delete the summary first, if one exists.
        if previous_summary is not None:

            summary_storage.delete_summary(normalized_id)

        try:

            # Delete the conversation after summary cleanup.
            self.storage.delete_session(normalized_id)

        except StorageError as error:

            # Restore the summary if conversation deletion failed.
            if previous_summary is not None:

                try:

                    summary_storage.save_summary(
                        previous_summary
                    )

                except StorageError as restore_error:

                    logger.exception(
                        "Conversation deletion failed and its summary "
                        "could not be restored."
                    )

                    raise StorageError(
                        "The conversation could not be deleted, "
                        "and its summary could not be restored. "
                        "Please check the application logs."
                    ) from restore_error

            logger.error(
                "Conversation deletion failed. "
                "The conversation remains available."
            )

            raise StorageError(
                "The conversation could not be deleted. "
                "Its summary was restored where applicable."
            ) from error

        logger.info(
            "Conversation and associated summary deleted: %s",
            normalized_id
        )

        return True
