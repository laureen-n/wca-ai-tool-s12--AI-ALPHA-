
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


logger = logging.getLogger("clinic_faq.summary_manager")


class SummaryManager:
    """
    Manages summaries and links them to their conversations.

    Role 1 generates the summary.
    Role 3 saves, retrieves and displays it.
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
        ).isoformat()

    # ======================================
    # SAVE SUMMARY
    # ======================================

    def save_summary(self, session_id, summary_text):

        if not isinstance(summary_text, str):
            raise ValueError("Summary must be text.")

        summary_text = summary_text.strip()

        if not summary_text:
            raise ValueError("Summary cannot be empty.")

        # Verify the conversation exists
        session = self.conversation_storage.load_session(
            session_id
        )

        session_id = session["session_id"]

        timestamp = self._current_timestamp()

        # Preserve the original creation time when updating
        try:

            previous_summary = self.summary_storage.load_summary(
                session_id
            )

            created_at = previous_summary["created_at"]

        except SummaryNotFoundError:

            previous_summary = None
            created_at = timestamp

        summary_data = {
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": timestamp,
            "summary": summary_text
        }

        updated_session = dict(session)

        updated_session["summary"] = summary_text
        updated_session["updated_at"] = timestamp

        # Save summary first
        self.summary_storage.save_summary(summary_data)

        try:

            # Update linked conversation
            self.conversation_storage.save_session(
                updated_session
            )

        except Exception as error:

            # Attempt to restore the previous summary
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
                    "Could not restore previous summary."
                )

            raise StorageError(
                "The summary could not be linked to its conversation."
            ) from error

        logger.info("Conversation summary saved and linked.")

        return summary_data

    # ======================================
    # GET SUMMARY
    # ======================================

    def get_summary(self, session_id):

        session = self.conversation_storage.load_session(
            session_id
        )

        summary = self.summary_storage.load_summary(
            session_id
        )

        if session["summary"] != summary["summary"]:

            raise StorageError(
                "The summary and conversation records do not match."
            )

        return summary

    # ======================================
    # LIST SUMMARIES
    # ======================================

    def list_summaries(self):

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
                        "A summary does not match its conversation."
                    )

            except StorageError:

                logger.warning(
                    "A summary has no valid conversation."
                )

        return summaries

    # ======================================
    # COUNT SUMMARIES
    # ======================================

    def count_summaries(self):

        return len(self.list_summaries())
