import questionary

from questionary import Choice, Style


# Shared styling and instructions for all interactive menus.
MENU_INSTRUCTION = "Use arrow keys to navigate and Enter to select."

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
        The selected action, or None if the menu was cancelled.
    """

    choices = [
        Choice("Start a new conversation", value="new"),
        Choice("Open an existing conversation", value="open"),
        Choice("View conversation history", value="history"),
        Choice("View saved summaries", value="summaries"),
        Choice("Delete a conversation", value="delete"),
        Choice("Exit application", value="exit"),
    ]

    return questionary.select(
        "What would you like to do?",
        choices=choices,
        style=MENU_STYLE,
        instruction=MENU_INSTRUCTION,
    ).ask()
