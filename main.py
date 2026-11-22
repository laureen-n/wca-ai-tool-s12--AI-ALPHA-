
from sessions.summary_manager import SummaryManager

from ui.summary_views import display_summaries

from rich.console import Console
from rich.panel import Panel

from sessions.manager import SessionManager

from ui.dashboard import show_dashboard

from ui.menus import main_menu

from ui.session_views import (
    display_sessions,
    select_session,
    run_conversation
)


console = Console()


# ==========================================
# INITIALIZE SESSION MANAGEMENT
# ==========================================

session_manager = SessionManager()

summary_manager = SummaryManager(
    conversation_storage=session_manager.storage
)


# ==========================================
# PAUSE APPLICATION
# ==========================================

def pause_application():
    """
    Wait for the user to press Enter.
    """

    try:
        input("\nPress Enter to return to the dashboard...")

    except (KeyboardInterrupt, EOFError):
        pass


# ==========================================
# START NEW CONVERSATION
# ==========================================

def start_new_conversation():
    """
    Create and open a new conversation.
    """

    try:
        session = session_manager.create_session()

        console.print(
            Panel(
                f"[green]A new conversation has been created.[/green]\n\n"
                f"[cyan]Session ID:[/cyan]\n"
                f"{session['session_id']}",
                title="NEW CONVERSATION",
                border_style="green"
            )
        )

        run_conversation(
            session_manager,
            session["session_id"]
        )

    except Exception as error:
        console.print(
            f"[bold red]Could not start conversation: {error}[/bold red]"
        )

        pause_application()


# ==========================================
# OPEN EXISTING CONVERSATION
# ==========================================

def open_existing_conversation():
    """
    Display saved conversations and allow the user to open one.
    """

    try:
        sessions = session_manager.list_sessions()

        if not sessions:
            console.print(
                Panel(
                    "[yellow]You have not created any conversations yet.[/yellow]",
                    title="NO SAVED CONVERSATIONS",
                    border_style="yellow"
                )
            )

            pause_application()
            return

        display_sessions(sessions)

        selected_session = select_session(sessions)

        if selected_session is None:
            return

        run_conversation(
            session_manager,
            selected_session
        )

    except Exception as error:
        console.print(
            f"[bold red]Could not open conversation: {error}[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW CONVERSATION HISTORY
# ==========================================

def view_conversation_history():
    """
    Display all saved conversation records.
    """

    try:
        sessions = session_manager.list_sessions()

        display_sessions(sessions)

        pause_application()

    except Exception as error:
        console.print(
            f"[bold red]Could not retrieve history: {error}[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW SAVED SUMMARIES
# ==========================================

def view_saved_summaries():
    """
    Display all saved and validated conversation summaries.
    """

    try:
        summaries = summary_manager.list_summaries()

        display_summaries(summaries)

        pause_application()

    except Exception as error:
        console.print(
            f"[bold red]Could not retrieve summaries: {error}[/bold red]"
        )

        pause_application()


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    """
    Main application controller.
    """

    console.print(
        "[bold bright_cyan]Starting Clinic Care Assistant...[/bold bright_cyan]"
    )

    while True:

        try:
            # Retrieve real dashboard statistics
            sessions = session_manager.list_sessions()

            total_conversations = len(sessions)

            total_summaries = summary_manager.count_summaries()

            # Show the updated dashboard
            show_dashboard(
                total_conversations=total_conversations,
                total_summaries=total_summaries
            )

            # Display main menu
            selected_option = main_menu()

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

            # Handle menu navigation
            if selected_option == "new":

                start_new_conversation()

            elif selected_option == "open":

                open_existing_conversation()

            elif selected_option == "history":

                view_conversation_history()

            elif selected_option == "summaries":

                view_saved_summaries()

            else:

                console.print(
                    "[bold red]Invalid menu selection.[/bold red]"
                )

                pause_application()

        except KeyboardInterrupt:

            console.print(
                "\n[yellow]Application interrupted safely.[/yellow]"
            )

            break

        except EOFError:

            console.print(
                "\n[yellow]Application closed.[/yellow]"
            )

            break


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()
