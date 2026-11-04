"""AI providers behind one small interface, so the rest of the app never imports an SDK.

AIAssistant and FileOrganizer only call:
    is_configured, generate(contents, vision=False), supports_file_upload,
    upload_file(path), delete_file(handle), max_prompt_files
GeminiClient (cloud) and OllamaClient (local, core/ollama.py) both provide them,
and AIRouter forwards to whichever one the user picked in Settings.
"""


class AIServiceError(Exception):
    pass


class AINotConfiguredError(AIServiceError):
    pass
