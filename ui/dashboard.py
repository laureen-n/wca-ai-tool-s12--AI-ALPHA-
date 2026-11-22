from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def show_dashboard(
    total_conversations: int = 0,
    total_summaries: int = 0
) -> None:
    """
    Display the main Clinic FAQ Assistant dashboard.

    Args:
        total_conversations: Number of saved conversations.
        total_summaries: Number of saved summaries.
    """

    console.clear()

    # Application branding
    brand = Text(
        "CLINIC CARE",
        style="bold bright_cyan"
    )

    tagline = Text(
        "AI-POWERED CLINIC FAQ ASSISTANT",
        style="dim"
    )

    header = Group(
        Align.center(brand),
        Align.center(tagline)
    )

    console.print(
        Panel(
            header,
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )
    )

    # Dashboard statistics
    statistics = Table.grid(
        expand=True,
        padding=(0, 1)
    )

    statistics.add_column(ratio=1)
    statistics.add_column(ratio=1)

    conversations_card = Panel(
        Align.center(
            Text(
                str(total_conversations),
                style="bold bright_white"
            )
        ),
        title="[bold]CONVERSATIONS[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )

    summaries_card = Panel(
        Align.center(
            Text(
                str(total_summaries),
                style="bold bright_white"
            )
        ),
        title="[bold]SAVED SUMMARIES[/bold]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )

    statistics.add_row(
        conversations_card,
        summaries_card
    )

    console.print(statistics)

    console.print()

    # Welcome message
    console.print(
        Align.center(
            Text(
                "Welcome to your clinic information workspace.",
                style="italic bright_white"
            )
        )
    )

    console.print(
        Align.center(
            Text(
                "Choose an option below to get started.",
                style="dim"
            )
        )
    )

    console.print()