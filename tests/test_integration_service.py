
import json

import pytest

from sessions.manager import SessionManager

from sessions.storage import ConversationStorage

from sessions.summary_storage import SummaryStorage

from sessions.summary_manager import SummaryManager

from services.assistant_service import (
    ClinicAssistantService,
    AIClientNotConfiguredError,
    AIResponseGenerationError,
    InvalidAIResponseError,
    SummaryGenerationError
)


# ==========================================
# TEST FIXTURE
# ==========================================

@pytest.fixture
def integration_system(tmp_path):

    conversation_storage = ConversationStorage(
        tmp_path / "conversations"
    )

    summary_storage = SummaryStorage(
        tmp_path / "summaries"
    )

    session_manager = SessionManager(
        storage=conversation_storage
    )

    summary_manager = SummaryManager(
        conversation_storage=conversation_storage,
        summary_storage=summary_storage
    )

    session = session_manager.create_session()

    return {
        "session_manager": session_manager,
        "summary_manager": summary_manager,
        "session": session
    }


# ==========================================
# VALID AI RESPONSE FACTORY
# ==========================================

def valid_ai_response():

    return json.dumps({
        "answer": "Please contact clinic reception to confirm opening hours.",
        "category": "Clinic information",
        "follow_up_question": "Would you like information about appointments?"
    })


# ==========================================
# TEST 1: SUCCESSFUL AI RESPONSE
# ==========================================

def test_successful_ai_response(integration_system):

    session_manager = integration_system["session_manager"]
    summary_manager = integration_system["summary_manager"]

    session = integration_system["session"]

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=summary_manager,
        response_generator=lambda history: valid_ai_response()
    )

    response = service.ask(
        session["session_id"],
        "What are your clinic opening hours?"
    )

    assert response["category"] == "Clinic information"

    history = session_manager.get_session_history(
        session["session_id"]
    )

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


# ==========================================
# TEST 2: INVALID JSON RETRY
# ==========================================

def test_invalid_json_gets_one_retry(integration_system):

    session_manager = integration_system["session_manager"]

    summary_manager = integration_system["summary_manager"]

    session = integration_system["session"]

    responses = iter([
        "{invalid json",
        valid_ai_response()
    ])

    calls = {"count": 0}

    def fake_generator(history):

        calls["count"] += 1

        return next(responses)

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=summary_manager,
        response_generator=fake_generator
    )

    response = service.ask(
        session["session_id"],
        "Do you offer laboratory services?"
    )

    assert calls["count"] == 2
    assert response["answer"]


# ==========================================
# TEST 3: REJECT TWO INVALID RESPONSES
# ==========================================

def test_two_invalid_responses_are_rejected(integration_system):

    session_manager = integration_system["session_manager"]

    session = integration_system["session"]

    calls = {"count": 0}

    def invalid_generator(history):

        calls["count"] += 1

        return "{invalid json"

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=integration_system["summary_manager"],
        response_generator=invalid_generator
    )

    with pytest.raises(InvalidAIResponseError):

        service.ask(
            session["session_id"],
            "What services do you offer?"
        )

    assert calls["count"] == 2

    # User's question remains saved
    history = session_manager.get_session_history(
        session["session_id"]
    )

    assert len(history) == 1
    assert history[0]["role"] == "user"


# ==========================================
# TEST 4: EMPTY QUESTION REJECTION
# ==========================================

def test_empty_question_rejected(integration_system):

    session_manager = integration_system["session_manager"]

    session = integration_system["session"]

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=integration_system["summary_manager"],
        response_generator=lambda history: valid_ai_response()
    )

    with pytest.raises(ValueError):

        service.ask(
            session["session_id"],
            "   "
        )

    assert session_manager.get_session_history(
        session["session_id"]
    ) == []


# ==========================================
# TEST 5: AI GENERATOR ERROR
# ==========================================

def test_ai_generator_error_is_handled(integration_system):

    session_manager = integration_system["session_manager"]

    session = integration_system["session"]

    def failing_generator(history):
        raise RuntimeError("Test API failure")

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=integration_system["summary_manager"],
        response_generator=failing_generator
    )

    with pytest.raises(AIResponseGenerationError):

        service.ask(
            session["session_id"],
            "What are your clinic services?"
        )

    # The question should remain saved
    history = session_manager.get_session_history(
        session["session_id"]
    )

    assert len(history) == 1


# ==========================================
# TEST 6: GENERATE AND SAVE SUMMARY
# ==========================================

def test_generate_and_save_summary(integration_system):

    session_manager = integration_system["session_manager"]

    summary_manager = integration_system["summary_manager"]

    session = integration_system["session"]

    session_manager.add_message(
        session["session_id"],
        "user",
        "What are your clinic opening hours?"
    )

    def fake_summary_generator(history):

        assert len(history) == 1

        return "The user requested information about clinic opening hours."

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=summary_manager,
        response_generator=lambda history: valid_ai_response(),
        summary_generator=fake_summary_generator
    )

    summary = service.generate_and_save_summary(
        session["session_id"]
    )

    assert summary["session_id"] == session["session_id"]

    assert "opening hours" in summary["summary"]

    assert summary_manager.count_summaries() == 1


# ==========================================
# TEST 7: MISSING AI GENERATOR
# ==========================================

def test_missing_ai_generator_is_handled(integration_system):

    service = ClinicAssistantService(
        session_manager=integration_system["session_manager"],
        summary_manager=integration_system["summary_manager"]
    )

    with pytest.raises(AIClientNotConfiguredError):

        service.ask(
            integration_system["session"]["session_id"],
            "What services do you offer?"
        )


# ==========================================
# TEST 8: EMPTY SUMMARY REJECTED
# ==========================================

def test_empty_generated_summary_rejected(integration_system):

    session_manager = integration_system["session_manager"]

    session = integration_system["session"]

    session_manager.add_message(
        session["session_id"],
        "user",
        "What are your clinic hours?"
    )

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=integration_system["summary_manager"],
        response_generator=lambda history: valid_ai_response(),
        summary_generator=lambda history: "   "
    )

    with pytest.raises(SummaryGenerationError):

        service.generate_and_save_summary(
            session["session_id"]
        )
