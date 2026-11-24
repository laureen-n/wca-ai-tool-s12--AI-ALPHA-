
from types import SimpleNamespace

from ui import session_views


def sample_session():
    return {
        "session_id": "session-12345678",
        "created_at": "2026-11-24T08:00:00",
        "updated_at": "2026-11-24T08:30:00",
        "messages": [
            {
                "role": "user",
                "message": "What are the emergency contact numbers?"
            },
            {
                "role": "assistant",
                "message": "Contact the hospital emergency department."
            }
        ],
        "summary": None
    }


def configure_inputs(monkeypatch, answers):
    """Provide predictable responses to interactive question prompts."""

    inputs = iter(answers)

    monkeypatch.setattr(
        session_views.questionary,
        "text",
        lambda prompt: SimpleNamespace(
            ask=lambda: next(inputs)
        )
    )


def test_existing_history_is_displayed_only_once(monkeypatch):
    """The conversation history should not be reprinted after every question."""

    session = sample_session()

    opened_sessions = []
    displayed_history = []
    displayed_user_messages = []
    displayed_responses = []
    ended_sessions = []

    class FakeSessionManager:

        def open_session(self, session_id):
            opened_sessions.append(session_id)
            return session

    class FakeAssistantService:

        def ask(self, session_id, question):
            return {
                "answer": "The hospital operates its main emergency department 24/7.",
                "category": "emergency",
                "follow_up_question": "Would you like the emergency contact numbers?"
            }

    configure_inputs(
        monkeypatch,
        [
            "What are the emergency opening hours?",
            "/back"
        ]
    )

    monkeypatch.setattr(
        session_views,
        "display_conversation",
        lambda selected: displayed_history.append(selected)
    )

    monkeypatch.setattr(
        session_views,
        "display_user_message",
        lambda message: displayed_user_messages.append(message)
    )

    monkeypatch.setattr(
        session_views,
        "display_ai_response",
        lambda response: displayed_responses.append(response)
    )

    monkeypatch.setattr(
        session_views,
        "display_session_ended",
        lambda *args, **kwargs: ended_sessions.append(True)
    )

    session_views.run_conversation(
        FakeSessionManager(),
        session["session_id"],
        FakeAssistantService()
    )

    assert opened_sessions == [session["session_id"]]
    assert displayed_history == [session]
    assert displayed_user_messages == [
        "What are the emergency opening hours?"
    ]
    assert len(displayed_responses) == 1
    assert ended_sessions == [True]


def test_offline_message_is_saved_and_displayed(monkeypatch):
    """Offline questions should be saved and displayed without an AI response."""

    session = sample_session()

    opened_sessions = []
    saved_messages = []
    displayed_user_messages = []
    offline_notices = []
    ended_sessions = []

    class FakeSessionManager:

        def open_session(self, session_id):
            opened_sessions.append(session_id)
            return session

        def add_message(self, session_id, role, message):
            saved_messages.append(
                (session_id, role, message)
            )

            return session

    configure_inputs(
        monkeypatch,
        [
            "Where is the hospital located?",
            "/back"
        ]
    )

    monkeypatch.setattr(
        session_views,
        "display_conversation",
        lambda selected: None
    )

    monkeypatch.setattr(
        session_views,
        "display_user_message",
        lambda message: displayed_user_messages.append(message)
    )

    monkeypatch.setattr(
        session_views,
        "display_offline_message",
        lambda: offline_notices.append(True)
    )

    monkeypatch.setattr(
        session_views,
        "display_session_ended",
        lambda *args, **kwargs: ended_sessions.append(True)
    )

    session_views.run_conversation(
        FakeSessionManager(),
        session["session_id"],
        assistant_service=None
    )

    assert opened_sessions == [session["session_id"]]

    assert saved_messages == [
        (
            session["session_id"],
            "user",
            "Where is the hospital located?"
        )
    ]

    assert displayed_user_messages == [
        "Where is the hospital located?"
    ]

    assert offline_notices == [True]
    assert ended_sessions == [True]


def test_summary_command_saves_and_ends_conversation(monkeypatch):
    """A successfully saved summary should end the active conversation."""

    session = sample_session()

    saved_summary = {
        "session_id": session["session_id"],
        "summary": "The user asked about hospital emergency services."
    }

    ended_messages = []

    class FakeSessionManager:

        def open_session(self, session_id):
            return session

    class FakeAssistantService:

        def generate_and_save_summary(self, session_id):
            assert session_id == session["session_id"]
            return saved_summary

    configure_inputs(
        monkeypatch,
        ["/summary"]
    )

    monkeypatch.setattr(
        session_views,
        "display_conversation",
        lambda selected: None
    )

    monkeypatch.setattr(
        session_views,
        "display_session_ended",
        lambda message=None: ended_messages.append(message)
    )

    session_views.run_conversation(
        FakeSessionManager(),
        session["session_id"],
        FakeAssistantService()
    )

    assert len(ended_messages) == 1
    assert "summary" in ended_messages[0].lower()


def test_cancelled_input_ends_conversation_safely(monkeypatch):
    """Cancelling the question prompt should end the session safely."""

    session = sample_session()

    ended_sessions = []

    class FakeSessionManager:

        def open_session(self, session_id):
            return session

    configure_inputs(
        monkeypatch,
        [None]
    )

    monkeypatch.setattr(
        session_views,
        "display_conversation",
        lambda selected: None
    )

    monkeypatch.setattr(
        session_views,
        "display_session_ended",
        lambda *args, **kwargs: ended_sessions.append(True)
    )

    session_views.run_conversation(
        FakeSessionManager(),
        session["session_id"],
        assistant_service=None
    )

    assert ended_sessions == [True]
