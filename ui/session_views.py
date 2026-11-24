
import logging
import questionary

from questionary import Choice

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sessions.storage import StorageError

from services.assistant_service import (
    AssistantIntegrationError
)


console = Console()

logger = logging.getLogger("clinic_faq.ui.session_views")


# ==========================================
# DISPLAY CONVERSATION HISTORY
# ==========================================

def display_sessions(sessions):
    """Display saved conversations in a professional table."""

    if not sessions:

        console.print(
            Panel(
                "[yellow]No conversations have been saved yet.[/yellow]",
                title="CONVERSATION HISTORY",
                border_style="yellow"
            )
        )

        return

    table = Table(
        title="SAVED CONVERSATIONS",
        show_header=True,
        header_style="bold bright_cyan"
    )

    table.add_column("Session ID", style="cyan")
    table.add_column("Created")
    table.add_column("Last Updated")
    table.add_column("Messages", justify="center")
    table.add_column("Summary", justify="center")

    for session in sessions:

        summary_status = (
            "Yes" if session.get("summary") else "No"
        )

        table.add_row(
            session["session_id"][:8],
            session["created_at"][:19].replace("T", " "),
            session["updated_at"][:19].replace("T", " "),
            str(len(session["messages"])),
            summary_status
        )

    console.print(table)


# ==========================================
# SELECT A SAVED SESSION
# ==========================================

def select_session(sessions):
    """Allow the user to select an existing conversation."""

    if not sessions:

        console.print(
            "[yellow]There are no saved conversations to open.[/yellow]"
        )

        return None

    choices = []

    for session in sessions:

        session_id = session["session_id"]

        label = (
            f"{session_id[:8]} | "
            f"{session['created_at'][:19].replace('T', ' ')} | "
            f"{len(session['messages'])} messages"
        )

        choices.append(
            Choice(label, value=session_id)
        )

    choices.append(
        Choice(
            "Return to main menu",
            value="__back__"
        )
    )

    selected = questionary.select(
        "Select a conversation to open:",
        choices=choices
    ).ask()

    if selected in (None, "__back__"):
        return None

    return selected


# ==========================================
# DISPLAY CONVERSATION
# ==========================================

def display_conversation(session):
    """Display the existing messages in a conversation."""

    console.print()

    console.print(
        Panel(
            Text(
                f"Session ID: {session['session_id']}\n"
                f"Created: {session['created_at']}",
                style="cyan"
            ),
            title="CONVERSATION",
            border_style="bright_cyan"
        )
    )

    messages = session["messages"]

    if not messages:

        console.print(
            "[dim]This conversation has no messages yet.[/dim]"
        )

        return

    for message in messages:

        if message["role"] == "user":

            title = "YOU"
            style = "bright_cyan"

        else:

            title = "CLINIC ASSISTANT"
            style = "bright_green"

        content = Text(
            message["message"],
            style="white"
        )

        console.print(
            Panel(
                content,
                title=title,
                border_style=style,
                padding=(1, 2)
            )
        )


# ==========================================
# DISPLAY A NEW USER MESSAGE
# ==========================================

def display_user_message(message):
    """Display only the newly submitted user message."""

    console.print(
        Panel(
            Text(message, style="white"),
            title="YOU",
            border_style="bright_cyan",
            padding=(1, 2)
        )
    )


# ==========================================
# DISPLAY SESSION END CONFIRMATION
# ==========================================

def display_session_ended(message=None):
    """Confirm that a conversation has ended."""

    if message is None:

        message = (
            "Your conversation has ended.\n"
            "Your previously saved messages remain available "
            "in conversation history."
        )

    console.print(
        Panel(
            Text(message, style="white"),
            title="CONVERSATION ENDED",
            border_style="green",
            padding=(1, 2)
        )
    )


# ==========================================
# DISPLAY AI RESPONSE
# ==========================================

def display_ai_response(response):
    """Display the validated AI response."""

    console.print(
        Panel(
            Text(
                response["answer"],
                style="white"
            ),
            title="CLINIC ASSISTANT",
            border_style="green",
            padding=(1, 2)
        )
    )

    console.print(
        f"[dim]Category: {response['category']}[/dim]"
    )

    if response["follow_up_question"]:

        console.print(
            Panel(
                Text(
                    response["follow_up_question"],
                    style="bright_white"
                ),
                title="FOLLOW-UP QUESTION",
                border_style="cyan"
            )
        )


# ==========================================
# DISPLAY OFFLINE MESSAGE
# ==========================================

def display_offline_message():
    """Explain that the question was saved without an AI response."""

    console.print(
        Panel(
            "[green]Your question has been saved successfully.[/green]\n\n"
            "[yellow]AI integration is currently unavailable. "
            "Your question is stored locally, but no AI response "
            "has been generated.[/yellow]",
            title="MESSAGE SAVED",
            border_style="yellow"
        )
    )


# ==========================================
# RUN AN ACTIVE CONVERSATION
# ==========================================

def run_conversation(
    session_manager,
    session_id,
    assistant_service=None
):
    """
    Run an interactive conversation session.

    Existing history is displayed once when the session opens.
    Only newly submitted messages and responses are displayed
    during the conversation.

    AI mode:
        The assistant service handles message saving and responses.

    Offline mode:
        User questions are saved locally.
    """

    # ======================================
    # LOAD CONVERSATION ONCE
    # ======================================

    try:

        session = session_manager.open_session(session_id)

    except StorageError:

        logger.exception(
            "Could not load the active conversation."
        )

        console.print(
            "[bold red]The conversation could not be loaded.[/bold red]"
        )

        return

    console.print(
        Panel(
            "[bold green]Conversation session opened successfully.[/bold green]\n\n"
            "[dim]Your messages are saved automatically.[/dim]\n\n"
            "[yellow]Do not enter patient names, identification numbers, "
            "or private medical records.[/yellow]\n\n"
            "[cyan]Commands: /back to return, /summary to generate a summary.[/cyan]",
            title="SESSION STARTED",
            border_style="green"
        )
    )

    # Display existing history only once.
    display_conversation(session)

    # ======================================
    # CONVERSATION INPUT LOOP
    # ======================================

    while True:

        try:

            user_message = questionary.text(
                "Enter your question:"
            ).ask()

        except (KeyboardInterrupt, EOFError):

            console.print(
                "\n[yellow]Conversation interrupted safely.[/yellow]"
            )

            display_session_ended()
            break

        if user_message is None:

            display_session_ended()
            break

        user_message = user_message.strip()

        if not user_message:

            console.print(
                "[yellow]Empty messages are not allowed.[/yellow]"
            )

            continue

        # ==================================
        # RETURN TO MAIN MENU
        # ==================================

        if user_message.lower() == "/back":

            display_session_ended()
            break

        # ==================================
        # GENERATE CONVERSATION SUMMARY
        # ==================================

        if user_message.lower() == "/summary":

            if assistant_service is None:

                console.print(
                    "[yellow]AI summary generation is unavailable "
                    "in offline mode.[/yellow]"
                )

                continue

            try:

                saved_summary = (
                    assistant_service.generate_and_save_summary(
                        session_id
                    )
                )

                console.print(
                    Panel(
                        Text(
                            saved_summary["summary"],
                            style="white"
                        ),
                        title="CONVERSATION SUMMARY SAVED",
                        border_style="green",
                        padding=(1, 2)
                    )
                )

                display_session_ended(
                    "Your conversation has ended.\n"
                    "Your messages and conversation summary "
                    "have been saved successfully."
                )

                break

            except AssistantIntegrationError as error:

                console.print(
                    f"[yellow]{error}[/yellow]"
                )

                continue

            except Exception:

                logger.exception(
                    "Unexpected summary generation failure."
                )

                console.print(
                    "[bold red]Could not generate the summary.[/bold red]"
                )

                continue

        # ==================================
        # OFFLINE MODE
        # ==================================

        if assistant_service is None:

            try:

                session_manager.add_message(
                    session_id,
                    "user",
                    user_message
                )

                display_user_message(user_message)

                display_offline_message()

            except (ValueError, StorageError) as error:

                logger.exception(
                    "Could not save an offline conversation message."
                )

                console.print(
                    f"[bold red]Could not save your question: {error}[/bold red]"
                )

            continue

        # ==================================
        # AI MODE
        # ==================================

        try:

            response = assistant_service.ask(
                session_id,
                user_message
            )

            # The assistant service has saved both messages.
            # Display only the new messages.
            display_user_message(user_message)

            display_ai_response(response)

        except AssistantIntegrationError as error:

            # The question is saved before AI generation in the
            # normal response-generation and validation failure paths.
            display_user_message(user_message)

            console.print(
                Panel(
                    f"[yellow]{error}[/yellow]\n\n"
                    "[dim]Your question has been saved in the conversation.[/dim]",
                    title="ASSISTANT RESPONSE UNAVAILABLE",
                    border_style="yellow"
                )
            )

            continue

        except Exception:

            logger.exception(
                "Unexpected conversation processing failure."
            )

            console.print(
                "[bold red]An unexpected error occurred while processing your question.[/bold red]"
            )

            display_session_ended()
            break
