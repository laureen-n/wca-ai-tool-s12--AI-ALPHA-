from questionary import Choice
import questionary

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def display_sessions(sessions):
    """
    Display all saved conversations in a professional table.
    """

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
    table.add_column("Created", style="white")
    table.add_column("Last Updated", style="white")
    table.add_column("Messages", justify="center")
    table.add_column("Summary", justify="center")

    for session in sessions:

        table.add_row(
            session["session_id"][:8],
            session["created_at"][:19].replace("T", " "),
            session["updated_at"][:19].replace("T", " "),
            str(len(session["messages"])),
            "Yes" if session.get("summary") else "No"
        )

    console.print(table)


def select_session(sessions):
    """
    Allow users to select a previously saved conversation.
    """

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


def display_conversation(session):
    """
    Display all messages belonging to a conversation.
    """

    console.print()

    console.print(
        Panel(
            f"[bold cyan]Session ID:[/bold cyan] "
            f"{session['session_id']}\n"
            f"[bold cyan]Created:[/bold cyan] "
            f"{session['created_at']}",
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

        role = message["role"].upper()

        if role == "USER":

            style = "bright_cyan"
            title = "YOU"

        else:

            style = "bright_green"
            title = "CLINIC ASSISTANT"

        # Text protects message content from being interpreted
        # as Rich formatting markup.
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


def run_conversation(session_manager, session_id):
    """
    Run a conversation session.

    User messages are saved automatically.
    AI responses will be connected during team integration.
    """

    console.print(
        Panel(
            "[bold green]Conversation session opened successfully.[/bold green]\n"
            "[dim]Your messages are saved automatically.[/dim]\n"
            "[yellow]Do not enter patient names, identification numbers, "
            "or private medical records.[/yellow]",
            title="SESSION STARTED",
            border_style="green"
        )
    )

    while True:

        try:

            session = session_manager.open_session(session_id)

            display_conversation(session)

            user_message = questionary.text(
                "Enter your question (type /back to return):"
            ).ask()

            if user_message is None:
                break

            user_message = user_message.strip()

            if user_message.lower() == "/back":
                break

            if not user_message:

                console.print(
                    "[yellow]Empty messages are not allowed.[/yellow]"
                )

                continue

            # Save the user's message
            updated_session = session_manager.add_message(
                session_id,
                "user",
                user_message
            )

            console.print(
                Panel(
                    "[green]Your question has been saved successfully.[/green]\n\n"
                    "[yellow]AI integration is pending. "
                    "The assistant will respond when Role 1's API module is connected.[/yellow]",
                    title="MESSAGE SAVED",
                    border_style="green"
                )
            )

        except KeyboardInterrupt:
            break