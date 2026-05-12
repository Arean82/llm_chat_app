# utils/constants.py
# This file contains constant values used throughout the LLM Chat App.

APP_NAME = "LLM Chat App"
APP_VERSION = "6.0.0"
APP_AUTHOR = "Arean Narrayan"

DEFAULT_MODEL_OPENAI = "gpt-4o"
DEFAULT_MODEL_GOOGLE = "gemini-1.5-flash"
DEFAULT_MODEL = DEFAULT_MODEL_OPENAI # General fallback
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT = 60

OPENAI_BASE_URL = "https://api.openai.com/v1"
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Universal API Server Security
API_SERVER_AUTH_KEY = "llm-local-auth-82c4f3eb0d"

# Connection settings
CONNECTION_CHECK_INTERVAL_CONNECTED_MS = 10000
CONNECTION_CHECK_INTERVAL_DISCONNECTED_MS = 3000
CONNECTION_TIMEOUT_SECONDS = 1

# API settings
API_TIMEOUT_SECONDS = 60
RATE_LIMIT_REQUESTS = 40
RATE_LIMIT_WINDOW_SECONDS = 60

# Chat settings
RESPONSE_BUFFER_CHARS = 64000
TYPING_INDICATOR_TEXT = "🤖 Assistant is typing..."