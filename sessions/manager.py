
import logging

from datetime import datetime, timezone
from uuid import uuid4

import memory as conversation_memory

from sessions.storage import ConversationStorage


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

    def create_session():

        timestamp = SessionManager._current_timestamp()

        session = {
            "session_id": str(uuid4()),
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": conversation_memory.create_history(),
            "summary": None
        }

        return session

    # ======================================
    # CREATE AND SAVE SESSION
    # ======================================

    def create_session(self):

        session = {
            "session_id": str(uuid4()),
            "created_at": self._current_timestamp(),
            "updated_at": self._current_timestamp(),
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
        """
        Add a message and automatically save the conversation.
        """

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

    def list_sessions():

        return ConversationStorage().list_sessions()

    def list_sessions(self):

        return self.storage.list_sessions()

    # ======================================
    # COUNT SESSIONS
    # ======================================

    def count_sessions(self):

        return len(self.list_sessions())
