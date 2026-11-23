
import json
import logging
import os
import tempfile

from datetime import datetime
from pathlib import Path

from sessions.storage import (
    ConversationStorage,
    StorageError,
    InvalidSessionDataError
)


logger = logging.getLogger("clinic_faq.summary_storage")


# ==========================================
# SUMMARY EXCEPTIONS
# ==========================================

class SummaryNotFoundError(StorageError):
    """Raised when a saved summary cannot be found."""


# ==========================================
# SUMMARY STORAGE
# ==========================================

class SummaryStorage:
    """
    Handles saving, loading, listing and deleting summaries.

    Each summary is stored in an individual JSON file
    linked to its original conversation session ID.
    """

    def __init__(self, summaries_dir=None):

        project_root = Path(__file__).resolve().parents[1]

        self.summaries_dir = (
            Path(summaries_dir)
            if summaries_dir is not None
            else project_root / "data" / "summaries"
        )

        try:
            self.summaries_dir.mkdir(
                parents=True,
                exist_ok=True
            )

        except OSError as error:
            raise StorageError(
                "Could not create the summaries directory."
            ) from error

    # ======================================
    # VALIDATE SUMMARY DATA
    # ======================================

    @classmethod
    def validate_summary_data(cls, summary_data):
        """Validate the structure of a summary."""

        if not isinstance(summary_data, dict):
            raise InvalidSessionDataError(
                "Summary data must be a dictionary."
            )

        required_fields = {
            "session_id",
            "created_at",
            "updated_at",
            "summary"
        }

        missing_fields = required_fields - summary_data.keys()

        if missing_fields:
            raise InvalidSessionDataError(
                f"Missing summary fields: {', '.join(sorted(missing_fields))}"
            )

        ConversationStorage.normalize_session_id(
            summary_data["session_id"]
        )

        # Validate timestamps
        for field in ("created_at", "updated_at"):

            value = summary_data[field]

            if not isinstance(value, str) or not value.strip():
                raise InvalidSessionDataError(
                    f"{field} must be a non-empty string."
                )

            try:
                datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )

            except ValueError as error:
                raise InvalidSessionDataError(
                    f"Invalid timestamp in {field}."
                ) from error

        # Validate summary text
        summary_text = summary_data["summary"]

        if not isinstance(summary_text, str) or not summary_text.strip():
            raise InvalidSessionDataError(
                "Summary text cannot be empty."
            )

    # ======================================
    # GET SUMMARY FILE PATH
    # ======================================

    def _get_summary_path(self, session_id):
        """Generate a safe summary file path."""

        normalized_id = ConversationStorage.normalize_session_id(
            session_id
        )

        return self.summaries_dir / f"{normalized_id}.json"

    # ======================================
    # SAVE SUMMARY
    # ======================================

    def save_summary(self, summary_data):
        """
        Save a summary using atomic file replacement.
        """

        if not isinstance(summary_data, dict):
            raise InvalidSessionDataError(
                "Summary data must be a dictionary."
            )

        # Work with a copy
        summary_data = dict(summary_data)

        # Normalize UUID
        summary_data["session_id"] = (
            ConversationStorage.normalize_session_id(
                summary_data.get("session_id")
            )
        )

        self.validate_summary_data(summary_data)

        session_id = summary_data["session_id"]

        file_path = self._get_summary_path(session_id)

        temp_path = None

        try:

            file_descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{session_id}.",
                suffix=".tmp",
                dir=self.summaries_dir
            )

            temp_path = Path(temp_name)

            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    summary_data,
                    file,
                    indent=4,
                    ensure_ascii=False,
                    allow_nan=False
                )

                file.write("\n")
                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temp_path,
                file_path
            )

            logger.info(
                "Conversation summary saved successfully."
            )

            return file_path

        except (OSError, TypeError, ValueError) as error:

            raise StorageError(
                "Could not save the summary."
            ) from error

        finally:

            if temp_path is not None and temp_path.exists():

                try:
                    temp_path.unlink()

                except OSError:
                    logger.warning(
                        "Could not remove an unfinished summary file."
                    )

    # ======================================
    # LOAD SUMMARY
    # ======================================

    def load_summary(self, session_id):
        """Retrieve a summary using its session ID."""

        file_path = self._get_summary_path(session_id)

        try:

            raw_content = file_path.read_text(
                encoding="utf-8"
            )

        except FileNotFoundError as error:

            raise SummaryNotFoundError(
                "No summary exists for this conversation."
            ) from error

        except UnicodeError as error:

            raise InvalidSessionDataError(
                "The summary file contains invalid UTF-8 data."
            ) from error

        except OSError as error:

            raise StorageError(
                "Could not read the summary file."
            ) from error

        try:

            summary_data = json.loads(raw_content)

        except json.JSONDecodeError as error:

            raise InvalidSessionDataError(
                "The summary file contains invalid JSON."
            ) from error

        self.validate_summary_data(summary_data)

        normalized_id = ConversationStorage.normalize_session_id(
            summary_data["session_id"]
        )

        if normalized_id != file_path.stem:

            raise InvalidSessionDataError(
                "The summary session ID does not match its filename."
            )

        summary_data["session_id"] = normalized_id

        return summary_data

    # ======================================
    # LIST ALL SUMMARIES
    # ======================================

    def list_summaries(self):
        """
        Retrieve all valid saved summaries.

        Corrupted files are skipped and logged.
        This prevents one damaged file from blocking
        access to other valid summaries.
        """

        summaries = []

        for file_path in self.summaries_dir.glob("*.json"):

            try:

                summary = self.load_summary(file_path.stem)

                summaries.append(summary)

            except StorageError:

                logger.warning(
                    "Skipping invalid summary file: %s",
                    file_path.name
                )

        # Most recently updated summaries appear first
        summaries.sort(
            key=lambda item: item["updated_at"],
            reverse=True
        )

        return summaries

    # ======================================
    # DELETE SUMMARY
    # ======================================

    def delete_summary(self, session_id):
        """Delete a summary by session ID."""

        file_path = self._get_summary_path(session_id)

        try:

            file_path.unlink()

        except FileNotFoundError as error:

            raise SummaryNotFoundError(
                "The requested summary does not exist."
            ) from error

        except OSError as error:

            raise StorageError(
                "Could not delete the summary."
            ) from error

        logger.info(
            "Conversation summary deleted successfully."
        )
