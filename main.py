from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ui.dashboard import show_dashboard
from ui.menus import main_menu


console = Console()


def pause_application() -> None:
    """
    Pause execution until the user presses Enter.
    """

    try:
        input("\nPress Enter to return to the dashboard...")

    except (KeyboardInterrupt, EOFError):
        pass


def show_feature_notice(feature_name: str) -> None:
    """
    Display a message for functionality
    that will be implemented in later milestones.
    """

    message = Text(
        f"{feature_name} will be implemented in an upcoming milestone.",
        style="bright_white"
    )

    console.print(
        Panel(
            message,
            title="FEATURE DEVELOPMENT",
            border_style="yellow"
        )
    )

    pause_application()


def main() -> None:
    """
    Main application controller.
    """

    console.print(
        "[bold bright_cyan]Starting Clinic Care Assistant...[/bold bright_cyan]"
    )

    while True:

        # Display dashboard
        show_dashboard()

        try:
            selected_option = main_menu()

        except KeyboardInterrupt:
            selected_option = "exit"

        except Exception as error:
            console.print(
                f"[bold red]Menu error: {error}[/bold red]"
            )
            break

        # Handle cancellation or exit
        if selected_option is None or selected_option == "exit":

            console.print(
                Panel(
                    "[bold green]Thank you for using Clinic Care Assistant![/bold green]",
                    title="APPLICATION CLOSED",
                    border_style="green"
                )
            )

            break

        # Navigate according to user selection
        if selected_option == "new":

            show_feature_notice("New conversation management")

        elif selected_option == "open":

            show_feature_notice("Existing conversation management")

        elif selected_option == "history":

            show_feature_notice("Conversation history")

        elif selected_option == "summaries":

            show_feature_notice("Saved summary management")

        else:

            console.print(
                "[bold red]Invalid menu selection.[/bold red]"
            )


if __name__ == "__main__":
    main()