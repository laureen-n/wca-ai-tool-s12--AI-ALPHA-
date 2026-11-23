
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
    """Display the messages belonging to a conversation."""

    console.print()

    console.print(
        Panel(
            Text(
                f"Session ID: {session['session_id']}\n"
                f"Created: {session['created_at']}",
                style="cyan"
            ),
            title="ACTIVE CONVERSATION",
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
# RUN AN ACTIVE CONVERSATION
# ==========================================

def run_conversation(
    session_manager,
    session_id,
    assistant_service=None
):
    """
    Run a conversation session.

    If the AI service is available:
        Questions are sent to the AI model.
        Responses are validated and saved.

    If the AI service is unavailable:
        Questions are saved locally.
    """

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

    while True:

        # Load latest conversation
        try:

            session = session_manager.open_session(session_id)

        except StorageError:

            logger.exception(
                "Could not load the active conversation."
            )

            console.print(
                "[bold red]The conversation could not be loaded.[/bold red]"
            )

            break

        display_conversation(session)

        # Receive user input
        try:

            user_message = questionary.text(
                "Enter your question:"
            ).ask()

        except (KeyboardInterrupt, EOFError):

            console.print(
                "\n[yellow]Returning from the conversation safely.[/yellow]"
            )

            break

        if user_message is None:
            break

        user_message = user_message.strip()

        if not user_message:

            console.print(
                "[yellow]Empty messages are not allowed.[/yellow]"
            )

            continue

        # Return to main menu
        if user_message.lower() == "/back":
            break

        # Generate a final summary
        if user_message.lower() == "/summary":

            if assistant_service is None:

                console.print(
                    "[yellow]AI summary generation is not connected yet. "
                    "Please integrate Role 1's AI module first.[/yellow]"
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

                # Return to dashboard after successful summarization
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

                console.print(
                    Panel(
                        "[green]Your question has been saved successfully.[/green]\n\n"
                        "[yellow]AI integration is pending. "
                        "The assistant will respond once Role 1's API is connected.[/yellow]",
                        title="MESSAGE SAVED",
                        border_style="green"
                    )
                )

            except (ValueError, StorageError) as error:

                console.print(
                    f"[red]Could not save your question: {error}[/red]"
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

            display_ai_response(response)

        except AssistantIntegrationError as error:

            console.print(
                Panel(
                    f"[yellow]{error}[/yellow]\n\n"
                    "[dim]Your question remains saved in the conversation.[/dim]",
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

            break
