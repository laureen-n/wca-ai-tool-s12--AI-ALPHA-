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


logger = logging.getLogger(__name__)


# ==========================================
# SUMMARY EXCEPTIONS
# ==========================================

class SummaryNotFoundError(StorageError):
    """Raised when a saved summary does not exist."""


# ==========================================
# SUMMARY STORAGE
# ==========================================

class SummaryStorage:
    """
    Handles persistent storage of conversation summaries.

    Each conversation has at most one current summary.
    A newly generated summary replaces the previous one.
    """

    def __init__(self, summaries_dir=None):

        project_root = Path(__file__).resolve().parents[1]

        self.summaries_dir = (
            Path(summaries_dir)
            if summaries_dir is not None
            else project_root / "data" / "summaries"
        )

        self.summaries_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    # ======================================
    # VALIDATE SUMMARY DATA
    # ======================================

    @staticmethod
    def validate_summary_data(summary_data):
        """
        Validate a summary before saving or returning it.
        """

        if not isinstance(summary_data, dict):

            raise InvalidSessionDataError(
                "Summary data must be a JSON object."
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
                "Missing summary fields: "
                + ", ".join(sorted(missing_fields))
            )

        ConversationStorage.normalize_session_id(
            summary_data["session_id"]
        )

        for field in ("created_at", "updated_at"):

            timestamp = summary_data[field]

            if not isinstance(timestamp, str) or not timestamp.strip():

                raise InvalidSessionDataError(
                    f"{field} must be a non-empty string."
                )

            try:

                datetime.fromisoformat(
                    timestamp.replace("Z", "+00:00")
                )

            except ValueError as error:

                raise InvalidSessionDataError(
                    f"Invalid {field} timestamp."
                ) from error

        summary_text = summary_data["summary"]

        if not isinstance(summary_text, str) or not summary_text.strip():

            raise InvalidSessionDataError(
                "Summary text cannot be empty."
            )

    # ======================================
    # GET SUMMARY FILE PATH
    # ======================================

    def _get_summary_path(self, session_id):

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

        self.validate_summary_data(summary_data)

        session_id = ConversationStorage.normalize_session_id(
            summary_data["session_id"]
        )

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
                "Summary for session %s saved successfully.",
                session_id
            )

            return file_path

        except (OSError, TypeError, ValueError) as error:

            raise StorageError(
                f"Could not save summary: {error}"
            ) from error

        finally:

            if temp_path is not None and temp_path.exists():

                try:
                    temp_path.unlink()

                except OSError:

                    logger.warning(
                        "Could not remove temporary summary file: %s",
                        temp_path
                    )

    # ======================================
    # LOAD SUMMARY
    # ======================================

    def load_summary(self, session_id):
        """
        Load a summary using its conversation session ID.
        """

        file_path = self._get_summary_path(session_id)

        try:

            raw_content = file_path.read_text(
                encoding="utf-8"
            )

        except FileNotFoundError:

            raise SummaryNotFoundError(
                "No summary exists for this conversation."
            )

        except UnicodeError as error:

            raise InvalidSessionDataError(
                "The summary file is not valid UTF-8."
            ) from error

        except OSError as error:

            raise StorageError(
                f"Could not read summary file: {error}"
            ) from error

        try:

            summary_data = json.loads(raw_content)

        except json.JSONDecodeError as error:

            raise InvalidSessionDataError(
                "The summary file contains invalid JSON."
            ) from error

        self.validate_summary_data(summary_data)

        if summary_data["session_id"] != file_path.stem:

            raise InvalidSessionDataError(
                "The summary session ID does not match its filename."
            )

        return summary_data

    # ======================================
    # LIST ALL SUMMARIES
    # ======================================

    def list_summaries(self):
        """
        Retrieve all valid saved summaries.

        Invalid files are skipped so that one corrupted
        summary does not prevent others from being viewed.
        """

        summaries = []

        for file_path in self.summaries_dir.glob("*.json"):

            try:

                summary = self.load_summary(file_path.stem)

                summaries.append(summary)

            except (StorageError, InvalidSessionDataError) as error:

                logger.warning(
                    "Skipping invalid summary %s: %s",
                    file_path.name,
                    error
                )

        summaries.sort(
            key=lambda item: item["updated_at"],
            reverse=True
        )

        return summaries

    # ======================================
    # DELETE SUMMARY
    # ======================================

    def delete_summary(self, session_id):
        """
        Delete a summary file.

        The calling manager is responsible for synchronizing
        the conversation record.
        """

        file_path = self._get_summary_path(session_id)

        try:

            file_path.unlink()

        except FileNotFoundError:

            raise SummaryNotFoundError(
                "The requested summary does not exist."
            )

        except OSError as error:

            raise StorageError(
                f"Could not delete summary: {error}"
            ) from error