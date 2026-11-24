
import questionary

from questionary import Choice

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from ui.menus import MENU_STYLE, MENU_INSTRUCTION

console = Console()


# ==========================================
# DISPLAY SAVED SUMMARY HISTORY
# ==========================================

def display_summaries(summaries):
    """Display saved summaries in a professional table."""

    if not summaries:

        console.print(
            Panel(
                "[yellow]No conversation summaries have been saved yet.[/yellow]",
                title="SAVED SUMMARIES",
                border_style="yellow"
            )
        )

        return

    table = Table(
        title="SUMMARY HISTORY",
        show_header=True,
        header_style="bold bright_cyan"
    )

    table.add_column("Session ID", style="cyan")
    table.add_column("Created")
    table.add_column("Updated")
    table.add_column("Preview")

    for summary in summaries:

        preview = summary["summary"].replace("\n", " ")

        if len(preview) > 60:
            preview = preview[:57] + "..."

        table.add_row(
            summary["session_id"][:8],
            summary["created_at"][:19].replace("T", " "),
            summary["updated_at"][:19].replace("T", " "),
            preview
        )

    console.print(table)


# ==========================================
# SELECT A SAVED SUMMARY
# ==========================================

def select_summary(summaries):
    """Allow the user to select an individual saved summary."""

    if not summaries:

        console.print(
            "[yellow]There are no saved summaries to open.[/yellow]"
        )

        return None

    choices = []

    for summary in summaries:

        session_id = summary["session_id"]

        preview = summary["summary"].replace("\n", " ")

        if len(preview) > 45:
            preview = preview[:42] + "..."

        label = (
            f"{session_id[:8]} | "
            f"{summary['created_at'][:19].replace('T', ' ')} | "
            f"{preview}"
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
        "Select a saved summary to view:",
        choices=choices,
        style=MENU_STYLE,
        instruction=MENU_INSTRUCTION,
    ).ask()

    if selected in (None, "__back__"):
        return None

    return selected


# ==========================================
# DISPLAY ONE SAVED SUMMARY
# ==========================================

def display_summary(summary):
    """Display the complete contents of one saved summary."""

    console.print(
        Panel(
            Text(
                summary["summary"],
                style="white"
            ),
            title=f"SAVED SUMMARY — SESSION {summary['session_id'][:8]}",
            border_style="green",
            padding=(1, 2)
        )
    )
