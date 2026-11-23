
import logging
import questionary

from questionary import Choice

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sessions.storage import StorageError


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
    """Allow a user to choose a saved conversation."""

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
            Choice(
                label,
                value=session_id
            )
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
# DISPLAY CONVERSATION MESSAGES
# ==========================================

def display_conversation(session):
    """Display the messages in a conversation."""

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

        # Treat user and assistant messages as plain text.
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
# RUN AN ACTIVE CONVERSATION
# ==========================================

def run_conversation(session_manager, session_id):
    """
    Run a conversation session.

    Messages are automatically saved.
    AI responses will be connected during team integration.
    """

    console.print(
        Panel(
            "[bold green]Conversation session opened successfully.[/bold green]\n\n"
            "[dim]Your messages are saved automatically.[/dim]\n\n"
            "[yellow]Do not enter patient names, identification numbers, "
            "or private medical records.[/yellow]",
            title="SESSION STARTED",
            border_style="green"
        )
    )

    while True:

        # Load the conversation
        try:

            session = session_manager.open_session(session_id)

        except StorageError:

            logger.exception(
                "Could not load an active conversation."
            )

            console.print(
                "[bold red]The conversation could not be loaded.[/bold red]"
            )

            break

        display_conversation(session)

        # Accept user input
        try:

            user_message = questionary.text(
                "Enter your question (type /back to return):"
            ).ask()

        except (KeyboardInterrupt, EOFError):

            console.print(
                "\n[yellow]Returning from the conversation safely.[/yellow]"
            )

            break

        # Handle cancellation
        if user_message is None:
            break

        user_message = user_message.strip()

        # Return to main menu
        if user_message.lower() == "/back":
            break

        # Reject empty input
        if not user_message:

            console.print(
                "[yellow]Empty messages are not allowed.[/yellow]"
            )

            continue

        # Save user message
        try:

            session_manager.add_message(
                session_id,
                "user",
                user_message
            )

        except ValueError as error:

            console.print(
                f"[yellow]Invalid input: {error}[/yellow]"
            )

            continue

        except StorageError:

            logger.exception(
                "Could not save a conversation message."
            )

            console.print(
                "[bold red]Your message could not be saved. "
                "Please try again.[/bold red]"
            )

            break

        # Confirm successful saving
        console.print(
            Panel(
                "[green]Your question has been saved successfully.[/green]\n\n"
                "[yellow]AI integration is pending. "
                "The assistant will respond when Role 1's API is connected.[/yellow]",
                title="MESSAGE SAVED",
                border_style="green"
            )
        )
