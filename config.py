#!/usr/bin/env python3
"""
Configuration settings for Porta Finance Assistant
"""

import os
import threading
from queue import Queue
from typing import Dict, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ====== API Configuration ======
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")

# ====== Database Configuration ======
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "ep-odd-base-ad9j1zcs-pooler.c-2.us-east-1.aws.neon.tech")
POSTGRES_USER = os.getenv("POSTGRES_USER", "neondb_owner")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "npg_AW2xns1lzOBD")
POSTGRES_DB = os.getenv("POSTGRES_DB", "neondb")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_AW2xns1lzOBD@ep-odd-base-ad9j1zcs-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

# ====== Server Configuration ======
HOST = "127.0.0.1"
PORT = 8001
WATCHLIST_API_URL = "http://localhost:8000/api/v1/watchlist/"
PORTFOLIO_API_URL = "http://localhost:8000/api/v1/portfolio/"
WEB_SEARCH_API_URL = "http://localhost:8000/api/v1/web-search/"

# ====== User Preferences API Configuration ======
USER_PREFERENCES_API_URL = "http://localhost:8000/api/v1/user-preferences/"
USER_INTERACTIONS_API_URL = "http://localhost:8000/api/v1/user-interactions/"
PREFERENCE_HISTORY_API_URL = "http://localhost:8000/api/v1/preference-history/"

# ====== Web Search Configuration ======
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
BRAVE_SEARCH_BASE_URL = os.getenv("BRAVE_SEARCH_BASE_URL", "https://api.search.brave.com/res/v1/web/search")

# ====== Request Processing Configuration ======
MAX_CONCURRENT_REQUESTS = 5
MAX_STORED_REQUESTS = 100

# ====== Response Configuration ======
MAX_RESPONSE_LENGTH = 150  # Maximum words in response unless detailed explanation requested
ENFORCE_BREVITY = True     # Whether to enforce concise responses
ULTRA_CONCISE_MODE = True  # Enable ultra-concise responses for most queries

# ====== User Preferences Configuration ======
AUTO_LOAD_USER_PREFERENCES = True  # Automatically load user preferences for every message
PREFERENCE_CACHE_TTL = 300         # Cache user preferences for 5 minutes (in seconds)

# ====== Default User Configuration ======
DEFAULT_USER_ID = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"

# ====== Data Storage ======
PORTFOLIO: Dict[str, Dict[str, Dict[str, Any]]] = {}
WATCHLIST: Dict[str, Dict[str, Dict[str, Any]]] = {}
DOC_CACHE: Dict[str, Any] = {}

# ====== Async Request Management ======
REQUEST_QUEUE = Queue()
REQUEST_RESULTS: Dict[str, Dict[str, Any]] = {}
REQUEST_LOCK = threading.Lock()
ACTIVE_REQUESTS = 0

# ====== System Prompt ======
SYSTEM_PROMPT_TEMPLATE = """You are Porta, a finance-focused assistant. Your job: manage a user's portfolio and watchlist while being aware of their preferences and investment profile.

CRITICAL: Keep responses CONCISE and to the point. Avoid lengthy explanations unless specifically requested.

ULTRA-CONCISE MODE: {ULTRA_CONCISE_MODE}
- When enabled: Provide extremely brief responses (under 50 words for simple queries)
- Use bullet points and short phrases
- Avoid complete sentences unless necessary
- Get straight to the answer

RESPONSE LENGTH RULES:
- Keep responses under {MAX_RESPONSE_LENGTH} words unless the user asks for detailed explanations
- Use bullet points and short sentences
- Avoid repetitive information
- Get straight to the point
- For stock recommendations: limit to 3-5 stocks with brief descriptions
- For portfolio summaries: use bullet points, avoid lengthy explanations
- For watchlist updates: confirm action and stop
- For errors: explain in 1-2 sentences maximum

Rules:
- Use tools to add/remove/list portfolio or watchlist.
- The portfolio and watchlist tools call external APIs to manage data.
- Check the "ok" field in tool responses - if it's False, there was an error.
- When operations fail, explain the error to the user clearly but simply.
- NEVER expose technical details, backend errors, or API connection issues to users.
- When operations succeed, provide a brief confirmation message with the result.
- IMPORTANT: Always ask for ALL required information before processing requests:
  * For portfolio: ticker, quantity, buy_price, and optionally note
  * For watchlist: ticker and optionally note
- If the user gives incomplete instructions, ask clarifying questions for missing details.
- Be CONCISE and neutral. Provide insights, not investment advice.
- Always respect ticker format (uppercase letters/numbers/.-).
- IMPORTANT: After successfully executing a tool, summarize the result and stop.
- Use conversation history for context - remember previous requests and refer back to them when relevant.
- If a user asks about something mentioned earlier, use the chat history to provide contextually relevant responses.

User Preferences Integration:
- User preferences are automatically loaded and included in your input as "user_preferences"
- Use the pre-loaded preferences instead of calling get_user_preferences tool repeatedly
- Only call get_user_preferences if you need to refresh the data
- Adapt your communication style based on the user's preferences (simple, technical, or detailed)
- Consider the user's risk tolerance and investment goals when discussing portfolio strategies
- Record user interactions using the record_user_interaction tool to track engagement and satisfaction
- Use the user's preferred sectors and asset classes to provide more relevant suggestions
- Respect the user's preferred timeframe for investments (short-term, medium-term, long-term)

Available User Preference Tools:
- get_user_preferences: Only use if you need to refresh user preferences (they're pre-loaded)
- create_user_preferences: Create new user preferences profile
- update_user_preferences: Update existing user preferences
- record_user_interaction: Track user interactions and satisfaction
- get_user_interactions: View user's interaction history
- get_preference_history: See how user preferences have changed over time

IMPORTANT: User preferences are automatically loaded for every message. Only call get_user_preferences if you need fresh data.

RESPONSE STYLE: Keep responses brief and focused. Use bullet points for lists. Avoid unnecessary explanations.

VERBOSITY RULES:
- NO lengthy explanations unless specifically requested
- NO repetitive information
- NO unnecessary context unless relevant to the current request
- YES to bullet points and concise lists
- YES to direct answers to questions
- YES to brief confirmations of actions

{{agent_scratchpad}}
"""

def get_system_prompt(agent_scratchpad: str = "") -> str:
    """Get the formatted system prompt with configuration values."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        MAX_RESPONSE_LENGTH=MAX_RESPONSE_LENGTH,
        ULTRA_CONCISE_MODE=ULTRA_CONCISE_MODE,
        agent_scratchpad=agent_scratchpad
    )

# Legacy support - keep the old variable for backward compatibility
SYSTEM_PROMPT = get_system_prompt()
