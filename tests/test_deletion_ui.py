
from types import SimpleNamespace

import main


def sample_session():
    return {
        "session_id": "e6b47a2e-8bc0-4d04-b7d4-a887d39b5eb1",
        "created_at": "2026-11-24T08:00:00",
        "updated_at": "2026-11-24T08:30:00",
        "messages": [
            {
                "role": "user",
                "message": "What are your opening hours?"
            }
        ],
        "summary": None
    }


def test_deletion_cancelled_does_not_delete(monkeypatch):

    session = sample_session()
    deleted = []
    paused = []

    fake_manager = SimpleNamespace(
        list_sessions=lambda: [session],
        open_session=lambda session_id: session,
        delete_session=lambda *args: deleted.append(args)
    )

    monkeypatch.setattr(main, "session_manager", fake_manager)
    monkeypatch.setattr(main, "summary_manager", object())
    monkeypatch.setattr(main, "display_sessions", lambda sessions: None)
    monkeypatch.setattr(
        main,
        "select_session",
        lambda sessions: session["session_id"]
    )
    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    monkeypatch.setattr(
        main.questionary,
        "confirm",
        lambda *args, **kwargs: SimpleNamespace(
            ask=lambda: False
        )
    )

    main.delete_conversation()

    assert deleted == []
    assert paused == []


def test_deletion_confirmed_calls_manager(monkeypatch):

    session = sample_session()
    deleted = []
    paused = []

    fake_manager = SimpleNamespace(
        list_sessions=lambda: [session],
        open_session=lambda session_id: session,
        delete_session=lambda *args: deleted.append(args)
    )

    fake_summary_manager = object()

    monkeypatch.setattr(main, "session_manager", fake_manager)
    monkeypatch.setattr(
        main,
        "summary_manager",
        fake_summary_manager
    )
    monkeypatch.setattr(main, "display_sessions", lambda sessions: None)
    monkeypatch.setattr(
        main,
        "select_session",
        lambda sessions: session["session_id"]
    )
    monkeypatch.setattr(
        main,
        "pause_application",
        lambda: paused.append(True)
    )

    monkeypatch.setattr(
        main.questionary,
        "confirm",
        lambda *args, **kwargs: SimpleNamespace(
            ask=lambda: True
        )
    )

    main.delete_conversation()

    assert deleted == [
        (session["session_id"], fake_summary_manager)
    ]

    assert paused == [True]
