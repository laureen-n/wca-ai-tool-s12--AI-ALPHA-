
import json
import sys

from ai_client import (
    generate_response,
    generate_summary,
    get_model_name,
    is_configured,
    AIClientRequestError,
    AIClientConfigurationError
)


REQUIRED_FAQ_FIELDS = [
    "answer",
    "category",
    "follow_up_question"
]

REQUIRED_SUMMARY_HEADINGS = [
    "CONVERSATION OVERVIEW",
    "KEY QUESTIONS AND TOPICS",
    "INFORMATION PROVIDED",
    "UNRESOLVED QUESTIONS",
    "FOLLOW-UP ACTIONS"
]


def validate_faq_response(raw_response):
    """Validate the structure and content of a Gemini FAQ response."""

    try:
        response = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise ValueError("Gemini returned invalid JSON.") from error

    if not isinstance(response, dict):
        raise ValueError("Gemini response must be a JSON object.")

    for field in REQUIRED_FAQ_FIELDS:
        value = response.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Missing, invalid or empty FAQ field: {field}"
            )

    return response


def validate_summary(summary):
    """Check that the summary contains all required sections."""

    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Gemini returned an empty summary.")

    missing_headings = [
        heading
        for heading in REQUIRED_SUMMARY_HEADINGS
        if heading.lower() not in summary.lower()
    ]

    if missing_headings:
        raise ValueError(
            "Summary is missing required sections: "
            + ", ".join(missing_headings)
        )

    return summary.strip()


def test_gemini_connection():
    """Test live Gemini FAQ generation and conversation summaries."""

    print("=" * 60)
    print("CLINIC FAQ ASSISTANT - LIVE GEMINI TEST")
    print("=" * 60)

    print(f"\nConfigured model: {get_model_name()}")
    print(f"API configured: {is_configured()}")

    if not is_configured():
        print("\nERROR: Gemini API key is missing.")
        print("Check your .env file.")
        return False

    faq_success = False
    summary_success = False

    history = [
        {
            "role": "user",
            "message": "What are your clinic opening hours?"
        }
    ]

    # --------------------------------------
    # TEST 1: FAQ GENERATION
    # --------------------------------------

    print("\n[TEST 1] Testing live FAQ generation...")

    try:
        raw_response = generate_response(history)
        response = validate_faq_response(raw_response)

        print("\nGEMINI FAQ RESPONSE:")
        print(json.dumps(response, indent=4, ensure_ascii=False))

        faq_success = True
        print("\nFAQ TEST: PASSED")

        summary_history = [
            {
                "role": "user",
                "message": history[0]["message"]
            },
            {
                "role": "assistant",
                "message": response["answer"]
            }
        ]

    except Exception as error:
        print("\nFAQ TEST: FAILED")
        print(f"Reason: {type(error).__name__}: {error}")

        summary_history = [
            {
                "role": "user",
                "message": history[0]["message"]
            }
        ]

    # --------------------------------------
    # TEST 2: SUMMARY GENERATION
    # --------------------------------------

    print("\n[TEST 2] Testing live summary generation...")

    try:
        summary = generate_summary(summary_history)
        summary = validate_summary(summary)

        print("\nGEMINI CONVERSATION SUMMARY:")
        print(summary)

        print(f"\nSummary character count: {len(summary)}")
        print(
            "Required sections found: "
            f"{len(REQUIRED_SUMMARY_HEADINGS)}/"
            f"{len(REQUIRED_SUMMARY_HEADINGS)}"
        )

        summary_success = True
        print("\nSUMMARY TEST: PASSED")

    except Exception as error:
        print("\nSUMMARY TEST: FAILED")
        print(f"Reason: {type(error).__name__}: {error}")

    # --------------------------------------
    # FINAL RESULTS
    # --------------------------------------

    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)

    print(f"FAQ generation: {'PASSED' if faq_success else 'FAILED'}")
    print(
        f"Summary generation: "
        f"{'PASSED' if summary_success else 'FAILED'}"
    )

    if faq_success and summary_success:
        print("\nALL LIVE GEMINI TESTS PASSED.")
        return True

    print("\nSOME LIVE GEMINI TESTS FAILED.")
    return False


if __name__ == "__main__":
    sys.exit(0 if test_gemini_connection() else 1)
