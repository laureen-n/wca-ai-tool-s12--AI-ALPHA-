
from types import SimpleNamespace

import main


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


def sample_summary():
    return {
        "session_id": "session-12345678",
        "summary": (
            "CONVERSATION OVERVIEW\n"
            "The user asked about emergency contacts."
        ),
        "created_at": "2026-11-24T08:30:00",
        "updated_at": "2026-11-24T08:30:00"
    }


def test_history_displays_conversation_without_starting_chat(monkeypatch):
    """History should display a session without entering interactive chat."""

    session = sample_session()

    fake_manager = SimpleNamespace(
        list_sessions=lambda: [session],
        open_session=lambda session_id: session
    )

    displayed_sessions = []
    displayed_conversations = []
    paused = []

    monkeypatch.setattr(
        main,
        "session_manager",
        fake_manager
    )

    monkeypatch.setattr(
        main,
        "display_sessions",
        lambda sessions: displayed_sessions.extend(sessions)
    )

    monkeypatch.setattr(
        main,
        "select_session",
        lambda sessions: session["session_id"]
    )

    monkeypatch.setattr(
        main,
        "display_conversation",
        lambda selected: displayed_conversations.append(selected)
    )

    monkeypatch.setattr(
        main,
        "run_conversation",
        lambda *args: (_ for _ in ()).throw(
            AssertionError("History must not start interactive chat.")
        )
    )

    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    main.view_conversation_history()

    assert displayed_sessions == [session]
    assert displayed_conversations == [session]
    assert paused == [True]


def test_history_handles_empty_session_list(monkeypatch):
    """History should handle the absence of saved conversations."""

    paused = []

    fake_manager = SimpleNamespace(
        list_sessions=lambda: []
    )

    monkeypatch.setattr(
        main,
        "session_manager",
        fake_manager
    )

    monkeypatch.setattr(
        main,
        "display_sessions",
        lambda sessions: None
    )

    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    main.view_conversation_history()

    assert paused == [True]


def test_saved_summaries_displays_selected_summary(monkeypatch):
    """The selected summary should be retrieved and displayed individually."""

    summaries = [sample_summary()]
    selected_summary = summaries[0]

    displayed_summaries = []
    displayed_summary = []
    retrieved_ids = []
    paused = []

    fake_manager = SimpleNamespace(
        list_summaries=lambda: summaries,
        get_summary=lambda session_id: (
            retrieved_ids.append(session_id) or selected_summary
        )
    )

    monkeypatch.setattr(
        main,
        "summary_manager",
        fake_manager
    )

    monkeypatch.setattr(
        main,
        "display_summaries",
        lambda items: displayed_summaries.extend(items)
    )

    monkeypatch.setattr(
        main,
        "select_summary",
        lambda items: selected_summary["session_id"]
    )

    monkeypatch.setattr(
        main,
        "display_summary",
        lambda summary: displayed_summary.append(summary)
    )

    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    main.view_saved_summaries()

    assert displayed_summaries == summaries
    assert retrieved_ids == [selected_summary["session_id"]]
    assert displayed_summary == [selected_summary]
    assert paused == [True]


def test_saved_summaries_handles_empty_list(monkeypatch):
    """The summary viewer should handle an empty summary history."""

    paused = []

    fake_manager = SimpleNamespace(
        list_summaries=lambda: []
    )

    monkeypatch.setattr(
        main,
        "summary_manager",
        fake_manager
    )

    monkeypatch.setattr(
        main,
        "display_summaries",
        lambda summaries: None
    )

    monkeypatch.setattr(
        main,
        "select_summary",
        lambda summaries: (
            _ for _ in ()
        ).throw(
            AssertionError("Should not ask for a summary when none exist.")
        )
    )

    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    main.view_saved_summaries()

    assert paused == [True]
