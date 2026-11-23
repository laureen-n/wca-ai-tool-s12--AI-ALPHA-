
import importlib

from rich.console import Console
from rich.panel import Panel

from core.logging_config import configure_logging

from sessions.manager import SessionManager
from sessions.summary_manager import SummaryManager

from services.assistant_service import ClinicAssistantService

from ui.dashboard import show_dashboard
from ui.menus import main_menu

from ui.session_views import (
    display_sessions,
    select_session,
    run_conversation
)

from ui.summary_views import display_summaries


# ==========================================
# APPLICATION INITIALIZATION
# ==========================================

console = Console()

logger = configure_logging()

session_manager = SessionManager()

summary_manager = SummaryManager(
    conversation_storage=session_manager.storage
)


# ==========================================
# LOAD ROLE 1 AI MODULE
# ==========================================

def build_assistant_service():
    """
    Load Role 1's AI functions and connect them
    to Role 2 and Role 3.

    Expected module:
        ai_client.py

    Expected functions:
        generate_response(history)
        generate_summary(history)
    """

    try:

        ai_module = importlib.import_module("ai_client")

    except ModuleNotFoundError as error:

        if error.name == "ai_client":

            logger.warning(
                "Role 1 AI module has not been installed."
            )

            return None

        raise

    response_generator = getattr(
        ai_module,
        "generate_response",
        None
    )

    summary_generator = getattr(
        ai_module,
        "generate_summary",
        None
    )

    if not callable(response_generator):

        logger.error(
            "ai_client.py is missing generate_response()."
        )

        return None

    if not callable(summary_generator):

        logger.error(
            "ai_client.py is missing generate_summary()."
        )

        return None

    logger.info(
        "Role 1 AI module loaded successfully."
    )

    return ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=summary_manager,
        response_generator=response_generator,
        summary_generator=summary_generator
    )


assistant_service = build_assistant_service()


# ==========================================
# PAUSE APPLICATION
# ==========================================

def pause_application():
    """Wait for the user to press Enter."""

    try:

        input("\nPress Enter to return to the dashboard...")

    except (KeyboardInterrupt, EOFError):
        pass


# ==========================================
# START NEW CONVERSATION
# ==========================================

def start_new_conversation():

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
            session["session_id"],
            assistant_service
        )

    except Exception:

        logger.exception(
            "Could not start a new conversation."
        )

        console.print(
            "[bold red]Could not start the conversation.[/bold red]"
        )

        pause_application()


# ==========================================
# OPEN EXISTING CONVERSATION
# ==========================================

def open_existing_conversation():

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
            selected_session,
            assistant_service
        )

    except Exception:

        logger.exception(
            "Could not open an existing conversation."
        )

        console.print(
            "[bold red]Could not open the conversation.[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW CONVERSATION HISTORY
# ==========================================

def view_conversation_history():

    try:

        sessions = session_manager.list_sessions()

        display_sessions(sessions)

        pause_application()

    except Exception:

        logger.exception(
            "Could not display conversation history."
        )

        console.print(
            "[bold red]Could not retrieve conversation history.[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW SAVED SUMMARIES
# ==========================================

def view_saved_summaries():

    try:

        summaries = summary_manager.list_summaries()

        display_summaries(summaries)

        pause_application()

    except Exception:

        logger.exception(
            "Could not retrieve saved summaries."
        )

        console.print(
            "[bold red]Could not retrieve summaries.[/bold red]"
        )

        pause_application()


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():

    console.print(
        "[bold bright_cyan]Starting Clinic Care Assistant...[/bold bright_cyan]"
    )

    if assistant_service is None:

        console.print(
            Panel(
                "[yellow]AI integration is not yet available.[/yellow]\n"
                "You can still create, save and reopen conversations.\n"
                "Contact the Role 1 developer to complete the Gemini connection.",
                title="OFFLINE MODE",
                border_style="yellow"
            )
        )

    else:

        console.print(
            "[bold green]AI assistant connected successfully.[/bold green]"
        )

    logger.info("Clinic Care Assistant started.")

    while True:

        try:

            # Calculate actual dashboard statistics
            total_conversations = session_manager.count_sessions()

            total_summaries = summary_manager.count_summaries()

            # Display dashboard
            show_dashboard(
                total_conversations=total_conversations,
                total_summaries=total_summaries
            )

            # Display main menu
            selected_option = main_menu()

            # Handle exit
            if selected_option is None or selected_option == "exit":

                console.print(
                    Panel(
                        "[bold green]Thank you for using Clinic Care Assistant![/bold green]",
                        title="APPLICATION CLOSED",
                        border_style="green"
                    )
                )

                logger.info("Clinic Care Assistant closed.")

                break

            # Navigate menu
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

            logger.info("Application interrupted by user.")

            break

        except EOFError:

            console.print(
                "\n[yellow]Application closed.[/yellow]"
            )

            logger.info("Application input stream closed.")

            break

        except Exception:

            logger.exception(
                "Unexpected error in the main application."
            )

            console.print(
                "\n[bold red]An unexpected application error occurred.[/bold red]"
            )

            console.print(
                "[dim]Technical details were recorded in the application log.[/dim]"
            )

            pause_application()


# ==========================================
# APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()
