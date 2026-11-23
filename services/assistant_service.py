
import logging

from json_validator import validate_response

from sessions.manager import SessionManager
from sessions.summary_manager import SummaryManager


logger = logging.getLogger("clinic_faq.assistant_service")


# ==========================================
# CUSTOM INTEGRATION EXCEPTIONS
# ==========================================

class AssistantIntegrationError(Exception):
    """Base exception for assistant integration."""


class AIClientNotConfiguredError(AssistantIntegrationError):
    """Raised when the AI client has not been configured."""


class AIResponseGenerationError(AssistantIntegrationError):
    """Raised when the AI model cannot generate a response."""


class InvalidAIResponseError(AssistantIntegrationError):
    """Raised when the AI returns invalid JSON after retrying."""


class SummaryGenerationError(AssistantIntegrationError):
    """Raised when an AI summary cannot be generated."""


# ==========================================
# ASSISTANT SERVICE
# ==========================================

class ClinicAssistantService:
    """
    Coordinates Role 1, Role 2 and Role 3.

    Role 1:
        Generates AI responses and summaries.

    Role 2:
        Validates JSON responses.

    Role 3:
        Saves questions, answers and summaries.
    """

    def __init__(
        self,
        session_manager,
        summary_manager,
        response_generator=None,
        summary_generator=None,
        response_validator=None
    ):

        self.session_manager = session_manager
        self.summary_manager = summary_manager

        # Dependency injection allows Role 1's AI functions
        # to be connected without changing this service.
        self.response_generator = response_generator

        self.summary_generator = summary_generator

        self.response_validator = (
            response_validator or validate_response
        )

    # ======================================
    # VALIDATE RESPONSE STRUCTURE
    # ======================================

    @staticmethod
    def _response_has_required_fields(response):
        """Confirm the required validated response fields exist."""

        if not isinstance(response, dict):
            return False

        required_fields = (
            "answer",
            "category",
            "follow_up_question"
        )

        for field in required_fields:

            value = response.get(field)

            if not isinstance(value, str) or not value.strip():
                return False

        return True

    # ======================================
    # ASK CLINIC FAQ
    # ======================================

    def ask(self, session_id, question):
        """
        Process a question through the complete AI workflow.

        Exactly one retry is attempted when JSON validation fails.

        Returns:
            A validated dictionary containing:
            answer, category and follow_up_question.
        """

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question cannot be empty.")

        if not callable(self.response_generator):
            raise AIClientNotConfiguredError(
                "The AI response generator is not configured."
            )

        # Confirm that the conversation exists
        self.session_manager.open_session(session_id)

        # Save the user's question first
        self.session_manager.add_message(
            session_id,
            "user",
            question.strip()
        )

        # Get updated conversation history
        history = self.session_manager.get_session_history(
            session_id
        )

        validated_response = None

        # Initial attempt + one retry
        for attempt in range(2):

            try:

                raw_response = self.response_generator(history)

            except Exception as error:

                logger.exception(
                    "The AI response generator failed."
                )

                raise AIResponseGenerationError(
                    "The AI assistant could not generate a response."
                ) from error

            try:

                if not isinstance(raw_response, str):
                    is_valid, parsed_response = False, None

                else:
                    is_valid, parsed_response = (
                        self.response_validator(raw_response)
                    )

                if (
                    is_valid
                    and self._response_has_required_fields(parsed_response)
                ):

                    validated_response = parsed_response
                    break

            except Exception:

                logger.exception(
                    "The AI response validator encountered an error."
                )

            logger.warning(
                "AI response validation failed. Attempt %s of 2.",
                attempt + 1
            )

        if validated_response is None:

            raise InvalidAIResponseError(
                "The AI returned an invalid response after one retry. "
                "Your question has been saved."
            )

        # Prepare the assistant message
        assistant_message = validated_response["answer"].strip()

        follow_up = validated_response["follow_up_question"].strip()

        if follow_up:

            assistant_message += (
                "\n\nFollow-up question: " + follow_up
            )

        # Save validated assistant response
        self.session_manager.add_message(
            session_id,
            "assistant",
            assistant_message
        )

        logger.info(
            "A validated assistant response was saved."
        )

        return validated_response

    # ======================================
    # GENERATE AND SAVE CONVERSATION SUMMARY
    # ======================================

    def generate_and_save_summary(self, session_id):
        """
        Generate a final summary and save it to the summary manager.

        Role 1 supplies the summary generator.
        Role 3 handles persistence.
        """

        if not callable(self.summary_generator):
            raise AIClientNotConfiguredError(
                "The AI summary generator is not configured."
            )

        # Retrieve conversation history
        history = self.session_manager.get_session_history(
            session_id
        )

        if not history:
            raise SummaryGenerationError(
                "An empty conversation cannot be summarized."
            )

        try:

            summary_text = self.summary_generator(history)

        except Exception as error:

            logger.exception(
                "The AI summary generator failed."
            )

            raise SummaryGenerationError(
                "The conversation summary could not be generated."
            ) from error

        if not isinstance(summary_text, str) or not summary_text.strip():

            raise SummaryGenerationError(
                "The AI returned an empty or invalid summary."
            )

        # Save summary through Role 3
        try:

            saved_summary = self.summary_manager.save_summary(
                session_id,
                summary_text.strip()
            )

        except Exception as error:

            logger.exception(
                "Could not save the generated summary."
            )

            raise SummaryGenerationError(
                "The generated summary could not be saved."
            ) from error

        logger.info(
            "Conversation summary generated and saved."
        )

        return saved_summary
