from datetime import datetime, timezone
from uuid import uuid4

import memory as conversation_memory

from sessions.storage import ConversationStorage


class SessionManager:
    """
    Manages the lifecycle of clinic FAQ conversations.

    Uses Role 2's memory.py for message history and
    ConversationStorage for persistent JSON storage.
    """

    def __init__(self, storage=None):

        self.storage = storage or ConversationStorage()

    @staticmethod
    def _current_timestamp():
        """Return the current UTC timestamp."""

        return datetime.now(timezone.utc).isoformat()

    def create_session(self):
        """Create and automatically save a new session."""

        timestamp = self._current_timestamp()

        session = {
            "session_id": str(uuid4()),
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": conversation_memory.create_history(),
            "summary": None
        }

        self.storage.save_session(session)

        return session

    def open_session(self, session_id):
        """Open a previously saved conversation."""

        return self.storage.load_session(session_id)

    def add_message(self, session_id, role, message):
        """
        Add a user or assistant message and save it immediately.
        """

        if role not in ("user", "assistant"):
            raise ValueError(
                "Role must be either 'user' or 'assistant'."
            )

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        # Always load the latest saved version first
        session = self.open_session(session_id)

        conversation_memory.add_to_history(
            session["messages"],
            role,
            message.strip()
        )

        session["updated_at"] = self._current_timestamp()

        self.storage.save_session(session)

        return session

    def get_session_history(self, session_id):
        """Retrieve the messages belonging to a session."""

        session = self.open_session(session_id)

        return conversation_memory.get_history(
            session["messages"]
        )

    def list_sessions(self):
        """Retrieve all saved conversations."""

        return self.storage.list_sessions()

    def count_sessions(self):
        """Count all valid saved conversations."""

        return len(self.list_sessions())