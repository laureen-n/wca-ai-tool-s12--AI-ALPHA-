from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


console = Console()


def display_summaries(summaries):
    """
    Display all saved conversation summaries.
    """

    if not summaries:

        console.print(
            Panel(
                "[yellow]No conversation summaries have been saved yet.[/yellow]",
                title="SAVED SUMMARIES",
                border_style="yellow"
            )
        )

        return

    console.print(
        "\n[bold bright_cyan]SAVED CONVERSATION SUMMARIES[/bold bright_cyan]\n"
    )

    table = Table(
        show_header=True,
        header_style="bold bright_cyan"
    )

    table.add_column("Session ID", style="cyan")
    table.add_column("Created")
    table.add_column("Last Updated")
    table.add_column("Summary Preview")

    for summary in summaries:

        preview = summary["summary"].replace("\n", " ")

        if len(preview) > 65:
            preview = preview[:62] + "..."

        table.add_row(
            summary["session_id"][:8],
            summary["created_at"][:19].replace("T", " "),
            summary["updated_at"][:19].replace("T", " "),
            preview
        )

    console.print(table)

    console.print()

    # Display the complete summary text
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