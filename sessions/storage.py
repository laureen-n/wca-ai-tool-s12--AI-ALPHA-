
import json
import logging
import os
import tempfile

from datetime import datetime
from pathlib import Path
from uuid import UUID


logger = logging.getLogger("clinic_faq.storage")


# ==========================================
# CUSTOM STORAGE EXCEPTIONS
# ==========================================

class StorageError(Exception):
    """Base exception for conversation storage errors."""


class SessionNotFoundError(StorageError):
    """Raised when a requested conversation does not exist."""


class InvalidSessionDataError(StorageError):
    """Raised when conversation data is invalid or corrupted."""


# ==========================================
# CONVERSATION STORAGE
# ==========================================

class ConversationStorage:
    """
    Handles saving, loading and listing conversations.

    Each conversation is stored in an individual JSON file.
    """

    def __init__(self, conversations_dir=None):

        project_root = Path(__file__).resolve().parents[1]

        self.conversations_dir = (
            Path(conversations_dir)
            if conversations_dir is not None
            else project_root / "data" / "conversations"
        )

        try:
            self.conversations_dir.mkdir(
                parents=True,
                exist_ok=True
            )

        except OSError as error:
            raise StorageError(
                "Could not create the conversation directory."
            ) from error

    # ======================================
    # SESSION ID VALIDATION
    # ======================================

    @staticmethod
    def normalize_session_id(session_id):
        """Validate and normalize a UUID."""

        if not isinstance(session_id, str):
            raise InvalidSessionDataError(
                "Session ID must be a string."
            )

        try:
            return str(UUID(session_id))

        except (ValueError, TypeError, AttributeError) as error:
            raise InvalidSessionDataError(
                "Invalid session ID. A valid UUID is required."
            ) from error

    # ======================================
    # TIMESTAMP VALIDATION
    # ======================================

    @staticmethod
    def validate_timestamp(value, field_name):
        """Validate an ISO-formatted timestamp."""

        if not isinstance(value, str) or not value.strip():
            raise InvalidSessionDataError(
                f"{field_name} must be a non-empty string."
            )

        try:
            datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

        except ValueError as error:
            raise InvalidSessionDataError(
                f"Invalid timestamp in {field_name}."
            ) from error

    # ======================================
    # SESSION DATA VALIDATION
    # ======================================

    @classmethod
    def validate_session_data(cls, session_data):
        """Validate the complete conversation structure."""

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
                f"Missing fields: {', '.join(sorted(missing_fields))}"
            )

        cls.normalize_session_id(session_data["session_id"])

        cls.validate_timestamp(
            session_data["created_at"],
            "created_at"
        )

        cls.validate_timestamp(
            session_data["updated_at"],
            "updated_at"
        )

        # Validate conversation messages
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

        # Summary can remain empty until generated
        summary = session_data["summary"]

        if summary is not None and not isinstance(summary, str):
            raise InvalidSessionDataError(
                "Summary must be text or null."
            )

    # ======================================
    # GET SESSION FILE PATH
    # ======================================

    def _get_session_path(self, session_id):

        normalized_id = self.normalize_session_id(session_id)

        return self.conversations_dir / f"{normalized_id}.json"

    # ======================================
    # SAVE SESSION
    # ======================================

    def save_session(self, session_data):
        """
        Save a conversation using atomic file replacement.

        A temporary file is written first to reduce the risk
        of leaving a partially written conversation.
        """

        if not isinstance(session_data, dict):
            raise InvalidSessionDataError(
                "Session data must be a dictionary."
            )

        # Work with a copy to protect caller data
        session_data = dict(session_data)

        # Normalize the session UUID
        session_data["session_id"] = self.normalize_session_id(
            session_data.get("session_id")
        )

        self.validate_session_data(session_data)

        session_id = session_data["session_id"]

        file_path = self._get_session_path(session_id)

        temp_path = None

        try:

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

            # Replace the old file only after successful writing
            os.replace(
                temp_path,
                file_path
            )

            logger.info(
                "Conversation saved successfully."
            )

            return file_path

        except (OSError, TypeError, ValueError) as error:

            raise StorageError(
                "Could not save the conversation."
            ) from error

        finally:

            # Remove unfinished temporary files
            if temp_path is not None and temp_path.exists():

                try:
                    temp_path.unlink()

                except OSError:
                    logger.warning(
                        "Could not remove an unfinished temporary file."
                    )

    # ======================================
    # READ AND VALIDATE SESSION FILE
    # ======================================

    def _read_session_file(self, file_path):
        """Read and validate a conversation JSON file."""

        try:

            raw_content = file_path.read_text(
                encoding="utf-8"
            )

        except FileNotFoundError as error:

            raise SessionNotFoundError(
                "The requested conversation does not exist."
            ) from error

        except UnicodeError as error:

            raise InvalidSessionDataError(
                "The conversation file contains invalid UTF-8 data."
            ) from error

        except OSError as error:

            raise StorageError(
                "Could not read the conversation file."
            ) from error

        try:

            session_data = json.loads(raw_content)

        except json.JSONDecodeError as error:

            raise InvalidSessionDataError(
                "The conversation file contains invalid JSON."
            ) from error

        self.validate_session_data(session_data)

        file_session_id = self.normalize_session_id(
            session_data["session_id"]
        )

        # Ensure file name matches its stored UUID
        if file_session_id != file_path.stem:

            raise InvalidSessionDataError(
                "The session ID does not match the filename."
            )

        session_data["session_id"] = file_session_id

        return session_data

    # ======================================
    # LOAD SESSION
    # ======================================

    def load_session(self, session_id):
        """Retrieve a conversation using its UUID."""

        file_path = self._get_session_path(session_id)

        return self._read_session_file(file_path)

    # ======================================
    # LIST ALL SESSIONS
    # ======================================

    def list_sessions(self):
        """
        Return all valid saved conversations.

        Invalid files are skipped and logged so one damaged
        file does not prevent access to other conversations.
        """

        sessions = []

        for file_path in self.conversations_dir.glob("*.json"):

            try:

                session = self._read_session_file(file_path)

                sessions.append(session)

            except StorageError:

                logger.warning(
                    "Skipping invalid conversation file: %s",
                    file_path.name
                )

        # Most recently updated conversations appear first
        sessions.sort(
            key=lambda item: item["updated_at"],
            reverse=True
        )

        return sessions
