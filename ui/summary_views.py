
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


console = Console()


# ==========================================
# DISPLAY SAVED SUMMARIES
# ==========================================

def display_summaries(summaries):
    """Display saved conversation summaries."""

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

    # Display full summary information
    for summary in summaries:

        console.print(
            Panel(
                Text(
                    summary["summary"],
                    style="white"
                ),
                title=f"SESSION {summary['session_id'][:8]}",
                border_style="green",
                padding=(1, 2)
            )
        )
