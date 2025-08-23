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

# ====== Request Processing Configuration ======
MAX_CONCURRENT_REQUESTS = 5
MAX_STORED_REQUESTS = 100

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
SYSTEM_PROMPT = """You are Porta, a finance-focused assistant. Your job: manage a user's portfolio and watchlist.

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
- Be concise and neutral. Provide insights, not investment advice.
- Always respect ticker format (uppercase letters/numbers/.-).
- IMPORTANT: After successfully executing a tool, summarize the result and stop.

{agent_scratchpad}
"""
