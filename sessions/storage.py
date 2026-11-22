import json
import logging
import os
import tempfile

from pathlib import Path
from uuid import UUID


logger = logging.getLogger(__name__)


# ==========================================
# CUSTOM STORAGE EXCEPTIONS
# ==========================================

class StorageError(Exception):
    """Base exception for conversation storage errors."""


class SessionNotFoundError(StorageError):
    """Raised when a requested session does not exist."""


class InvalidSessionDataError(StorageError):
    """Raised when session data is invalid or corrupted."""


# ==========================================
# CONVERSATION STORAGE
# ==========================================

class ConversationStorage:
    """
    Handles saving, loading and listing conversations.

    Each conversation is stored in an individual JSON file.
    """

    def __init__(self, conversations_dir=None):

        # Find the project root automatically
        project_root = Path(__file__).resolve().parents[1]

        # Set the default conversation directory
        self.conversations_dir = (
            Path(conversations_dir)
            if conversations_dir is not None
            else project_root / "data" / "conversations"
        )

        # Ensure the storage directory exists
        self.conversations_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # ======================================
    # SESSION ID VALIDATION
    # ======================================

    @staticmethod
    def normalize_session_id(session_id):
        """
        Validate and normalize a UUID.

        This also prevents unsafe file paths.
        """

        if not isinstance(session_id, str):
            raise InvalidSessionDataError(
                "Session ID must be a string."
            )

        try:
            return str(UUID(session_id))

        except (ValueError, AttributeError, TypeError):

            raise InvalidSessionDataError(
                "Invalid session ID. Expected a valid UUID."
            )

    # ======================================
    # SESSION DATA VALIDATION
    # ======================================

    @classmethod
    def validate_session_data(cls, session_data):
        """
        Validate the structure of a conversation.
        """

        if not isinstance(session_data, dict):
            raise InvalidSessionDataError(
                "Session data must be a JSON object."
            )

        required_fields = {
            "session_id",
            "created_at",
            "updated_at",
            "messages",
            "summary"
        }

        missing_fields = required_fields - session_data.keys()

        if missing_fields:
            raise InvalidSessionDataError(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )

        cls.normalize_session_id(session_data["session_id"])

        # Validate timestamps
        from datetime import datetime

        for field in ("created_at", "updated_at"):

            value = session_data[field]

            if not isinstance(value, str) or not value.strip():
                raise InvalidSessionDataError(
                    f"{field} must be a non-empty string."
                )

            try:
                datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )

            except ValueError:
                raise InvalidSessionDataError(
                    f"Invalid timestamp in field: {field}"
                )

        # Validate message history
        messages = session_data["messages"]

        if not isinstance(messages, list):
            raise InvalidSessionDataError(
                "Messages must be stored as a list."
            )

        for index, message in enumerate(messages):

            if not isinstance(message, dict):
                raise InvalidSessionDataError(
                    f"Message {index} must be an object."
                )

            if message.get("role") not in ("user", "assistant"):
                raise InvalidSessionDataError(
                    f"Message {index} has an invalid role."
                )

            content = message.get("message")

            if not isinstance(content, str) or not content.strip():
                raise InvalidSessionDataError(
                    f"Message {index} must contain non-empty text."
                )

        # Summary can be empty until generated
        summary = session_data["summary"]

        if summary is not None and not isinstance(summary, str):
            raise InvalidSessionDataError(
                "Summary must be text or null."
            )

    # ======================================
    # GET CONVERSATION FILE PATH
    # ======================================

    def _get_session_path(self, session_id):

        normalized_id = self.normalize_session_id(session_id)

        return self.conversations_dir / f"{normalized_id}.json"

    # ======================================
    # SAVE CONVERSATION
    # ======================================

    def save_session(self, session_data):
        """
        Save a conversation safely using an atomic file replacement.

        The temporary file prevents an interrupted write from
        leaving a partially written conversation file.
        """

        self.validate_session_data(session_data)

        session_id = self.normalize_session_id(
            session_data["session_id"]
        )

        file_path = self._get_session_path(session_id)

        temp_path = None

        try:

            # Create a temporary file in the same directory
            file_descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{session_id}.",
                suffix=".tmp",
                dir=self.conversations_dir
            )

            temp_path = Path(temp_name)

            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    session_data,
                    file,
                    indent=4,
                    ensure_ascii=False,
                    allow_nan=False
                )

                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            # Replace the previous file with the new version
            os.replace(
                temp_path,
                file_path
            )

            logger.info(
                "Session %s saved successfully.",
                session_id
            )

            return file_path

        except (OSError, TypeError, ValueError) as error:

            raise StorageError(
                f"Could not save conversation: {error}"
            ) from error

        finally:

            # Remove an unfinished temporary file if necessary
            if temp_path is not None and temp_path.exists():

                try:
                    temp_path.unlink()

                except OSError:
                    logger.warning(
                        "Could not remove temporary file: %s",
                        temp_path
                    )

    # ======================================
    # READ AND VALIDATE A CONVERSATION FILE
    # ======================================

    def _read_session_file(self, file_path):

        try:

            raw_content = file_path.read_text(
                encoding="utf-8"
            )

        except FileNotFoundError:

            raise SessionNotFoundError(
                "The requested conversation could not be found."
            )

        except OSError as error:

            raise StorageError(
                f"Could not read conversation file: {error}"
            ) from error

        try:

            session_data = json.loads(raw_content)

        except (json.JSONDecodeError, UnicodeError) as error:

            raise InvalidSessionDataError(
                "The conversation file contains invalid JSON."
            ) from error

        self.validate_session_data(session_data)

        # Verify that the file name matches the session ID
        file_session_id = self.normalize_session_id(
            session_data["session_id"]
        )

        if file_session_id != file_path.stem:

            raise InvalidSessionDataError(
                "The session ID does not match the file name."
            )

        return session_data

    # ======================================
    # LOAD CONVERSATION
    # ======================================

    def load_session(self, session_id):
        """
        Retrieve an existing conversation by UUID.
        """

        file_path = self._get_session_path(session_id)

        return self._read_session_file(file_path)

    # ======================================
    # LIST ALL CONVERSATIONS
    # ======================================

    def list_sessions(self):
        """
        Return all valid saved conversations.

        Invalid files are skipped and logged so one damaged
        file does not prevent access to other conversations.
        """

        sessions = []

        if not self.conversations_dir.exists():
            return sessions

        for file_path in self.conversations_dir.glob("*.json"):

            try:

                session = self._read_session_file(file_path)

                sessions.append(session)

            except StorageError as error:

                logger.warning(
                    "Skipping invalid conversation file %s: %s",
                    file_path.name,
                    error
                )

        # Most recently updated conversations appear first
        sessions.sort(
            key=lambda item: item["updated_at"],
            reverse=True
        )

        return sessions