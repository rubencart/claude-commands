"""Minimal standard-library client for Mistral chat completions."""

import json
import os
import urllib.error
import urllib.request


DEFAULT_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "zai-glm-5-3"


def chat_completion(messages, model=DEFAULT_MODEL, max_tokens=8192):
    """Send a chat completion request and return its text content."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    payload = json.dumps(
        {"model": model, "messages": messages, "max_tokens": max_tokens}
    ).encode("utf-8")
    request = urllib.request.Request(
        os.environ.get("MISTRAL_API_ENDPOINT", DEFAULT_ENDPOINT),
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        message = f"Mistral API HTTP {error.code}"
        if error.code in {400, 401, 402, 429}:
            message += {
                400: " (bad request)",
                401: " (invalid or missing credentials)",
                402: " (payment or credit issue)",
                429: " (rate limit exceeded)",
            }[error.code]
        if details:
            message += f": {details}"
        raise RuntimeError(message) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Mistral API: {error.reason}") from error

    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"Unexpected Mistral response: {response_data}") from error

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            item["text"]
            for item in content
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
        ]
        if text_parts:
            return "".join(text_parts)
    raise RuntimeError(f"Mistral response contained no text content: {response_data}")
