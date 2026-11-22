import questionary

from questionary import Choice, Style


# Custom colour scheme for the interactive menu
MENU_STYLE = Style([
    ("qmark", "fg:#00D7AF bold"),
    ("question", "bold"),
    ("answer", "fg:#00D7AF bold"),
    ("pointer", "fg:#00D7AF bold"),
    ("highlighted", "fg:#00D7AF bold"),
    ("selected", "fg:#00D7AF"),
    ("instruction", "fg:#888888"),
])


def main_menu() -> str | None:
    """
    Display the main interactive application menu.

    Returns:
        A string representing the selected action,
        or None if the menu was cancelled.
    """

    choices = [
        Choice(
            "Start a new conversation",
            value="new"
        ),

        Choice(
            "Open an existing conversation",
            value="open"
        ),

        Choice(
            "View conversation history",
            value="history"
        ),

        Choice(
            "View saved summaries",
            value="summaries"
        ),

        Choice(
            "Exit application",
            value="exit"
        ),
    ]

    selected_option = questionary.select(
        "What would you like to do?",
        choices=choices,
        style=MENU_STYLE,
        instruction="Use arrow keys to navigate and Enter to select."
    ).ask()

    return selected_option