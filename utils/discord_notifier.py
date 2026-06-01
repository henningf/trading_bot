"""Discord webhook varsling."""

import requests


def _chunk_text(text: str, max_len: int = 1900) -> list[str]:
    """Deler lange meldinger i Discord-vennlige biter."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_len
        chunks.append(text[start:end])
        start = end
    return chunks


def send_discord_message(webhook_url: str, message: str) -> bool:
    """Sender melding til Discord via webhook."""
    if not webhook_url:
        return False

    for chunk in _chunk_text(message):
        response = requests.post(
            webhook_url,
            json={"content": chunk},
            timeout=20,
        )
        if response.status_code < 200 or response.status_code >= 300:
            return False

    return True
