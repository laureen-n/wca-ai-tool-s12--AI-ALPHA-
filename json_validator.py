
# ==========================================
# JSON VALIDATION
# This file checks AI responses before display.
# ==========================================

import json


def validate_response(ai_response):

    # Step 1: Try converting the AI response into JSON
    try:
        response = json.loads(ai_response)

    except json.JSONDecodeError:
        return False, None

    # Step 2: Check that the response is a dictionary
    if not isinstance(response, dict):
        return False, None

    # Step 3: Define the required JSON fields
    required_fields = [
        "answer",
        "category",
        "follow_up_question"
    ]

    # Step 4: Check whether all required fields exist
    for field in required_fields:
        if field not in response:
            return False, None

    # Step 5: Check that all fields contain text
    for field in required_fields:
        if not isinstance(response[field], str):
            return False, None

        if not response[field].strip():
            return False, None

    # Step 6: If all checks pass, return the response
    return True, response
