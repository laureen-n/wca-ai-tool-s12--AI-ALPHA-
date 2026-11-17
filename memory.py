
# ==========================================
# CONVERSATION MEMORY
# This file manages the conversation history.
# ==========================================


def create_history():
    # Create an empty list to store conversations
    history = []

    return history


def add_to_history(history, role, message):
    # Add a user's question or AI's answer to history
    history.append({
        "role": role,
        "message": message
    })


def get_history(history):
    # Return all previous messages
    return history


def clear_history(history):
    # Remove all messages when the session ends
    history.clear()
