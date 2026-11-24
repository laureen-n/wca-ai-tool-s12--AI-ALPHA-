
import importlib

import questionary

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
    display_conversation,
    run_conversation
)

from ui.summary_views import (
    display_summaries,
    select_summary,
    display_summary
)


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
    Load Role 1's Gemini client and connect it
    to Roles 2 and 3.
    """

    try:

        ai_module = importlib.import_module("ai_client")

    except ModuleNotFoundError as error:

        missing_package = error.name or ""

        if missing_package == "ai_client":

            logger.warning(
                "Role 1 AI module has not been created."
            )

        elif (
            missing_package == "google"
            or missing_package.startswith("google.")
            or missing_package == "dotenv"
        ):

            logger.error(
                "Gemini dependencies are missing. "
                "Install requirements.txt."
            )

        else:

            logger.exception(
                "An AI module dependency could not be imported."
            )

        return None

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

    configuration_checker = getattr(
        ai_module,
        "is_configured",
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

    if not callable(configuration_checker):

        logger.error(
            "ai_client.py is missing is_configured()."
        )

        return None

    if not configuration_checker():

        logger.warning(
            "Gemini API key is not configured."
        )

        return None

    service = ClinicAssistantService(
        session_manager=session_manager,
        summary_manager=summary_manager,
        response_generator=response_generator,
        summary_generator=summary_generator
    )

    logger.info(
        "Gemini AI assistant configured successfully."
    )

    return service


# Initialize AI integration
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
            "[bold red]Could not start the conversation. "
            "Please check the application logs.[/bold red]"
        )

        pause_application()


# ==========================================
# OPEN EXISTING CONVERSATION
# ==========================================

def open_existing_conversation():
    """Open a saved conversation and allow the user to continue it."""

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

        # This option intentionally starts interactive chat mode.
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
            "[bold red]Could not open the conversation. "
            "Please check the application logs.[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW CONVERSATION HISTORY
# ==========================================

def view_conversation_history():
    """Allow users to inspect a saved conversation without editing it."""

    try:

        sessions = session_manager.list_sessions()

        if not sessions:

            display_sessions(sessions)
            pause_application()
            return

        display_sessions(sessions)

        selected_session = select_session(sessions)

        if selected_session is None:
            return

        # Load the selected conversation without starting chat mode.
        session = session_manager.open_session(
            selected_session
        )

        display_conversation(session)

        pause_application()

    except Exception:

        logger.exception(
            "Could not display conversation history."
        )

        console.print(
            "[bold red]Could not retrieve or display the selected conversation.[/bold red]"
        )

        pause_application()


# ==========================================
# VIEW SAVED SUMMARIES
# ==========================================

def view_saved_summaries():
    """Allow users to browse and view individual saved summaries."""

    try:

        summaries = summary_manager.list_summaries()

        display_summaries(summaries)

        if not summaries:

            pause_application()
            return

        selected_summary = select_summary(summaries)

        if selected_summary is None:
            return

        # Retrieve the selected summary through SummaryManager.
        summary = summary_manager.get_summary(
            selected_summary
        )

        display_summary(summary)

        pause_application()

    except Exception:

        logger.exception(
            "Could not retrieve or display saved summaries."
        )

        console.print(
            "[bold red]Could not retrieve or display the selected summary.[/bold red]"
        )

        pause_application()


# ==========================================
# DELETE CONVERSATION
# ==========================================

def delete_conversation():
    """Allow the user to delete a conversation after confirmation."""

    try:

        sessions = session_manager.list_sessions()

        if not sessions:

            console.print(
                Panel(
                    "[yellow]There are no conversations available to delete.[/yellow]",
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

        # Display the selected conversation before confirmation.
        selected_data = session_manager.open_session(
            selected_session
        )

        console.print(
            Panel(
                f"[cyan]Session ID:[/cyan] {selected_session}\n"
                f"[cyan]Messages:[/cyan] {len(selected_data['messages'])}\n"
                f"[cyan]Has summary:[/cyan] "
                f"{'Yes' if selected_data.get('summary') else 'No'}",
                title="SELECTED CONVERSATION",
                border_style="yellow"
            )
        )

        confirmed = questionary.confirm(
            "Permanently delete this conversation and its saved summary?",
            default=False
        ).ask()

        if confirmed is not True:

            console.print(
                Panel(
                    "[yellow]Deletion cancelled. "
                    "No conversation data was changed.[/yellow]",
                    title="DELETION CANCELLED",
                    border_style="yellow"
                )
            )

            return

        session_manager.delete_session(
            selected_session,
            summary_manager
        )

        console.print(
            Panel(
                "[bold green]The conversation and its associated summary "
                "were successfully deleted.[/bold green]",
                title="DELETION COMPLETE",
                border_style="green"
            )
        )

        logger.info(
            "User deleted conversation: %s",
            selected_session
        )

        pause_application()

    except Exception:

        logger.exception(
            "Could not delete the selected conversation."
        )

        console.print(
            Panel(
                "[bold red]The conversation could not be deleted. "
                "Please check the application logs.[/bold red]",
                title="DELETION FAILED",
                border_style="red"
            )
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
                "[yellow]AI integration is not configured.[/yellow]\n\n"
                "You can still create, save and reopen conversations.\n"
                "Check your .env file and Gemini API dependencies.",
                title="OFFLINE MODE",
                border_style="yellow"
            )
        )

    else:

        console.print(
            Panel(
                "[bold green]Gemini AI assistant connected successfully.[/bold green]",
                title="AI MODE",
                border_style="green"
            )
        )

    logger.info("Clinic Care Assistant started.")

    while True:

        try:

            total_conversations = session_manager.count_sessions()

            total_summaries = summary_manager.count_summaries()

            show_dashboard(
                total_conversations=total_conversations,
                total_summaries=total_summaries
            )

            selected_option = main_menu()

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

            if selected_option == "new":

                start_new_conversation()

            elif selected_option == "open":

                open_existing_conversation()

            elif selected_option == "history":

                view_conversation_history()

            elif selected_option == "summaries":

                view_saved_summaries()

            elif selected_option == "delete":

                delete_conversation()

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
