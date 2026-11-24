
import json

from types import SimpleNamespace

import pytest

import ai_client

from ai_client import (
    AIClientConfigurationError,
    AIClientRequestError,
    generate_response,
    generate_summary,
    is_configured
)


# ==========================================
# FAKE GEMINI CLIENT FOR TESTING
# ==========================================

class FakeModels:

    def __init__(self, output_text):
        self.output_text = output_text
        self.last_request = None

    def generate_content(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(text=self.output_text)


class FakeGeminiClient:

    def __init__(self, output_text):
        self.models = FakeModels(output_text)


# ==========================================
# SAMPLE CONVERSATION
# ==========================================

SAMPLE_HISTORY = [
    {
        "role": "user",
        "message": "What are your clinic opening hours?"
    }
]


VALID_JSON_RESPONSE = json.dumps({
    "answer": "Please contact clinic reception to confirm opening hours.",
    "category": "Opening hours",
    "follow_up_question": "Would you like information about appointments?"
})


REQUIRED_SUMMARY_HEADINGS = [
    "CONVERSATION OVERVIEW",
    "KEY QUESTIONS AND TOPICS",
    "INFORMATION PROVIDED",
    "UNRESOLVED QUESTIONS",
    "FOLLOW-UP ACTIONS"
]


# ==========================================
# TEST 1: API KEY CONFIGURATION
# ==========================================

def test_is_configured_without_api_key(monkeypatch):

    monkeypatch.delenv(
        "GEMINI_API_KEY",
        raising=False
    )

    assert is_configured() is False


def test_is_configured_with_api_key(monkeypatch):

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-api-key"
    )

    assert is_configured() is True


# ==========================================
# TEST 2: MISSING API KEY
# ==========================================

def test_missing_api_key_raises_error(monkeypatch):

    monkeypatch.delenv(
        "GEMINI_API_KEY",
        raising=False
    )

    monkeypatch.setattr(
        ai_client,
        "_client",
        None
    )

    monkeypatch.setattr(
        ai_client,
        "_client_api_key",
        None
    )

    with pytest.raises(AIClientConfigurationError):
        ai_client._get_client()


# ==========================================
# TEST 3: INVALID HISTORY
# ==========================================

def test_invalid_history_rejected():

    with pytest.raises(ValueError):
        generate_response([
            {
                "role": "admin",
                "message": "Invalid role"
            }
        ])


# ==========================================
# TEST 4: EMPTY HISTORY
# ==========================================

def test_empty_history_rejected():

    with pytest.raises(ValueError):
        generate_response([])


# ==========================================
# TEST 5: SUCCESSFUL FAQ GENERATION
# ==========================================

def test_generate_response(monkeypatch):

    fake_client = FakeGeminiClient(
        VALID_JSON_RESPONSE
    )

    monkeypatch.setattr(
        ai_client,
        "_get_client",
        lambda: fake_client
    )

    monkeypatch.setattr(
        ai_client,
        "_load_clinic_information",
        lambda: "Opening hours: Monday to Friday, 8 AM to 5 PM."
    )

    response = generate_response(SAMPLE_HISTORY)

    parsed_response = json.loads(response)

    assert parsed_response["answer"]
    assert parsed_response["category"] == "Opening hours"
    assert parsed_response["follow_up_question"]

    request = fake_client.models.last_request

    assert request["model"] == ai_client.get_model_name()
    assert "CONVERSATION HISTORY" in request["contents"]
    assert "R - ROLE" in request["config"]["system_instruction"]

    assert (
        "Opening hours: Monday to Friday"
        in request["config"]["system_instruction"]
    )

    assert request["config"]["response_mime_type"] == "application/json"

    assert (
        request["config"]["response_json_schema"]["required"]
        == [
            "answer",
            "category",
            "follow_up_question"
        ]
    )

    assert request["config"]["max_output_tokens"] == 700


# ==========================================
# TEST 6: SUMMARY GENERATION
# ==========================================

def test_generate_summary(monkeypatch):

    expected_summary = """
CONVERSATION OVERVIEW
The user requested information about opening hours.

KEY QUESTIONS AND TOPICS
The user asked about clinic opening hours.

INFORMATION PROVIDED
The assistant advised the user to contact reception.

UNRESOLVED QUESTIONS
The exact opening hours remain unconfirmed.

FOLLOW-UP ACTIONS
Contact clinic reception to confirm opening hours.
""".strip()

    fake_client = FakeGeminiClient(
        expected_summary
    )

    monkeypatch.setattr(
        ai_client,
        "_get_client",
        lambda: fake_client
    )

    summary = generate_summary(SAMPLE_HISTORY)

    assert summary == expected_summary

    request = fake_client.models.last_request

    assert request["model"] == ai_client.get_model_name()
    assert request["contents"]

    prompt = request["config"]["system_instruction"]

    for heading in REQUIRED_SUMMARY_HEADINGS:
        assert heading in prompt

    assert "Never omit a heading" in prompt
    assert "None identified" in prompt

    assert "response_mime_type" not in request["config"]
    assert "response_json_schema" not in request["config"]

    assert request["config"]["max_output_tokens"] == 1200


# ==========================================
# TEST 7: SUMMARY PROMPT COMPLETENESS
# ==========================================

def test_summary_prompt_requires_all_headings():

    prompt = ai_client.FINAL_SUMMARY_PROMPT

    assert len(REQUIRED_SUMMARY_HEADINGS) == 5

    for heading in REQUIRED_SUMMARY_HEADINGS:
        assert heading in prompt

    assert "exactly" in prompt.lower()
    assert "never omit" in prompt.lower()


# ==========================================
# TEST 8: EMPTY GEMINI RESPONSE
# ==========================================

def test_empty_gemini_response_rejected(monkeypatch):

    fake_client = FakeGeminiClient("")

    monkeypatch.setattr(
        ai_client,
        "_get_client",
        lambda: fake_client
    )

    monkeypatch.setattr(
        ai_client,
        "_load_clinic_information",
        lambda: "No verified clinic information."
    )

    with pytest.raises(AIClientRequestError):
        generate_response(SAMPLE_HISTORY)


# ==========================================
# TEST 9: DEFAULT MODEL
# ==========================================

def test_default_model_name():

    assert ai_client.get_model_name()
    assert isinstance(ai_client.get_model_name(), str)


# ==========================================
# TEST 10: GEMINI 503 ERROR HANDLING
# ==========================================

def test_gemini_503_error_handled(monkeypatch):

    class FakeServerError(Exception):
        code = 503

    class FailingModels:

        def generate_content(self, **kwargs):
            raise FakeServerError("503 Service Unavailable")

    fake_client = SimpleNamespace(
        models=FailingModels()
    )

    monkeypatch.setattr(
        ai_client,
        "_get_client",
        lambda: fake_client
    )

    monkeypatch.setattr(
        ai_client,
        "_load_clinic_information",
        lambda: "No verified clinic information."
    )

    with pytest.raises(
        AIClientRequestError,
        match="temporarily unavailable"
    ):
        generate_response(SAMPLE_HISTORY)


# ==========================================
# TEST 11: STRICT CLINIC INFORMATION GROUNDING
# ==========================================

def test_system_prompt_requires_approved_information_only():

    prompt = ai_client.build_system_prompt(
        "Clinic name: Example Hospital"
    )

    assert "ONLY approved source" in prompt
    assert "Do not use your general knowledge" in prompt
    assert "Never invent doctors' names" in prompt
    assert "not confirmed" in prompt


# ==========================================
# TEST 12: QUALIFIED INFORMATION MUST BE PRESERVED
# ==========================================

def test_system_prompt_preserves_information_qualifications():

    prompt = ai_client.build_system_prompt(
        "Clinic hours: Approximately 8 AM to 5 PM."
    )

    assert "approximate" in prompt.lower()
    assert "Never convert an estimate" in prompt
    assert "do not guarantee" in prompt.lower()


# ==========================================
# TEST 13: EMERGENCY HANDLING
# ==========================================

def test_system_prompt_includes_emergency_instructions():

    prompt = ai_client.build_system_prompt(
        "Emergency contact: +254 703 082 000"
    )

    assert "EMERGENCIES" in prompt
    assert "immediate in-person emergency medical attention" in prompt
    assert "approved hospital emergency" in prompt


# ==========================================
# TEST 14: MISSING INFORMATION FALLBACK
# ==========================================

def test_system_prompt_requires_missing_information_fallback():

    prompt = ai_client.build_system_prompt(
        "Clinic name: Example Hospital"
    )

    assert "I don't have confirmed information about that." in prompt
    assert "Please contact The Nairobi Hospital directly" in prompt
