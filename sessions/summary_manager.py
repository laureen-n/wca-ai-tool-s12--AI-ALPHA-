import logging

from datetime import datetime, timezone

from sessions.storage import (
    ConversationStorage,
    StorageError
)

from sessions.summary_storage import (
    SummaryStorage,
    SummaryNotFoundError
)


logger = logging.getLogger(__name__)


# ==========================================
# SUMMARY MANAGEMENT
# ==========================================

class SummaryManager:
    """
    Coordinates conversation summaries and their sessions.

    Role 1 supplies the AI-generated summary text.
    Role 3 saves, retrieves and manages that summary.
    """

    def __init__(
        self,
        conversation_storage=None,
        summary_storage=None
    ):

        self.conversation_storage = (
            conversation_storage or ConversationStorage()
        )

        self.summary_storage = (
            summary_storage or SummaryStorage()
        )

    # ======================================
    # CURRENT TIMESTAMP
    # ======================================

    @staticmethod
    def _current_timestamp():

        return datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds")

    # ======================================
    # SAVE SUMMARY
    # ======================================

    def save_summary(self, session_id, summary_text):
        """
        Save a summary and update its original conversation.

        Args:
            session_id: ID of an existing conversation.
            summary_text: Summary text returned by the AI model.

        Returns:
            The saved summary dictionary.
        """

        if not isinstance(summary_text, str):

            raise ValueError(
                "Summary must be provided as text."
            )

        summary_text = summary_text.strip()

        if not summary_text:

            raise ValueError(
                "Summary cannot be empty."
            )

        # Verify that the conversation exists
        session = self.conversation_storage.load_session(
            session_id
        )

        timestamp = self._current_timestamp()

        # Preserve the original summary creation time
        try:

            previous_summary = self.summary_storage.load_summary(
                session_id
            )

            created_at = previous_summary["created_at"]

        except SummaryNotFoundError:

            previous_summary = None

            created_at = timestamp

        summary_data = {
            "session_id": session["session_id"],
            "created_at": created_at,
            "updated_at": timestamp,
            "summary": summary_text
        }

        # Synchronize the conversation record
        previous_session = dict(session)

        session["summary"] = summary_text
        session["updated_at"] = timestamp

        # Save the summary JSON first
        self.summary_storage.save_summary(
            summary_data
        )

        try:

            # Update the original conversation JSON
            self.conversation_storage.save_session(
                session
            )

        except Exception as error:

            # Attempt to restore the previous summary file
            try:

                if previous_summary is None:

                    self.summary_storage.delete_summary(
                        session_id
                    )

                else:

                    self.summary_storage.save_summary(
                        previous_summary
                    )

            except StorageError:

                logger.exception(
                    "Summary rollback failed for session %s.",
                    session_id
                )

            raise StorageError(
                "The summary was saved, but the conversation "
                "record could not be updated. "
                "Please check the storage files."
            ) from error

        logger.info(
            "Summary successfully linked to session %s.",
            session_id
        )

        return summary_data

    # ======================================
    # GET ONE SUMMARY
    # ======================================

    def get_summary(self, session_id):
        """
        Retrieve a summary and verify its original session.
        """

        # Ensure its original conversation still exists
        session = self.conversation_storage.load_session(
            session_id
        )

        summary = self.summary_storage.load_summary(
            session_id
        )

        # Check the two stored records agree
        if session["summary"] != summary["summary"]:

            raise StorageError(
                "Summary information does not match its conversation."
            )

        return summary

    # ======================================
    # LIST ALL SUMMARIES
    # ======================================

    def list_summaries(self):
        """
        Return summaries linked to existing conversations.
        """

        summaries = []

        for summary in self.summary_storage.list_summaries():

            try:

                session = self.conversation_storage.load_session(
                    summary["session_id"]
                )

                if session["summary"] == summary["summary"]:

                    summaries.append(summary)

                else:

                    logger.warning(
                        "Summary and conversation are inconsistent: %s",
                        summary["session_id"]
                    )

            except StorageError as error:

                logger.warning(
                    "Skipping summary with unavailable session: %s",
                    error
                )

        return summaries

    # ======================================
    # SUMMARY COUNT
    # ======================================

    def count_summaries(self):

        return len(self.list_summaries())