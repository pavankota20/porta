#!/usr/bin/env python3
"""
Porta Finance Assistant API
A FastAPI-based financial portfolio and watchlist management system with AI assistance.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, constr
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import time
import uuid
import requests
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.callbacks import BaseCallbackHandler

# ====== Configuration ======
MAX_CONCURRENT_REQUESTS = 5
MAX_STORED_REQUESTS = 100

# ====== Data Models ======
Ticker = constr(pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")

class AddPortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    weight: Optional[float] = None
    note: Optional[str] = None

class RemovePortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker

class ListPortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")

class AddWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    note: Optional[str] = None

class RemoveWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker

class ListWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")

class GetNewsInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    lookback_days: int = Field(default=3, ge=1, le=30)

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to perform web search for")
    max_results: Optional[int] = Field(default=5, description="Maximum number of results to return")

# ====== API Models ======
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/prompt")
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", description="User identifier")
    chat_history: List[Dict[str, str]] = Field(default=[], description="Previous chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(default="success", description="Response status")

class AsyncChatRequest(BaseModel):
    message: str = Field(..., description="User's message/prompt")
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", description="User identifier")
    chat_history: List[Dict[str, str]] = Field(default=[], description="Previous chat history")

class AsyncChatResponse(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(..., description="Request status")
    message: str = Field(..., description="Status message")

class RequestStatusResponse(BaseModel):
    request_id: str = Field(..., description="Unique request identifier")
    status: str = Field(..., description="Request status")
    response: Optional[str] = Field(None, description="Agent's response")
    user_id: str = Field(..., description="User identifier")
    error: Optional[str] = Field(None, description="Error message if any")
    created_at: str = Field(..., description="Request creation timestamp")
    completed_at: Optional[str] = Field(None, description="Request completion timestamp")


PORTFOLIO: Dict[str, Dict[str, Dict[str, Any]]] = {}
WATCHLIST: Dict[str, Dict[str, Dict[str, Any]]] = {}  
DOC_CACHE: Dict[str, Any] = {}

# ====== Async Request Management ======
REQUEST_QUEUE = Queue()
REQUEST_RESULTS: Dict[str, Dict[str, Any]] = {}
REQUEST_LOCK = threading.Lock()
ACTIVE_REQUESTS = 0
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)

# ====== Helper Functions ======
def _pf(user_id: str) -> Dict[str, Dict[str, Any]]:
    """Get user portfolio, create if doesn't exist"""
    return PORTFOLIO.setdefault(user_id, {})

def _wl(user_id: str) -> Dict[str, Dict[str, Any]]:
    """Get user watchlist, create if doesn't exist"""
    return WATCHLIST.setdefault(user_id, {})



# ====== LangChain Tools ======
@tool("add_to_portfolio", args_schema=AddPortfolioInput)
def add_to_portfolio(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = "",
                     weight: Optional[float] = None, note: Optional[str] = None):
    """Add or upsert a holding in the user's portfolio."""
    try:
        print(f"[LOG] add_to_portfolio called with user_id={user_id}, ticker={ticker}, weight={weight}, note={note}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to add {ticker} for user {user_id}")
        
        # Validate weight if provided
        if weight is not None and (weight < 0 or weight > 100):
            print(f"[LOG] Validation failed: weight is invalid ({weight})")
            return {"ok": False, "error": "Weight must be between 0 and 100"}
        
        pf = _pf(user_id)
        existed = ticker in pf
        
        pf[ticker] = {"weight": weight, "note": note}
        
        # Verify the entry was actually added
        if ticker in pf:
            print(f"[LOG] Successfully added {ticker} to portfolio")
            return {
                "ok": True, 
                "message": f"{'Updated' if existed else 'Added'} {ticker} in portfolio",
                "portfolio": pf,
                "portfolio_count": len(pf)
            }
        else:
            print(f"[LOG] Failed to add ticker {ticker} to portfolio")
            return {"ok": False, "error": "Failed to add ticker to portfolio"}
            
    except Exception as e:
        print(f"[LOG] Error adding to portfolio: {str(e)}")
        return {"ok": False, "error": f"Error adding to portfolio: {str(e)}"}

@tool("remove_from_portfolio", args_schema=RemovePortfolioInput)
def remove_from_portfolio(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = ""):
    """Remove a holding from the user's portfolio."""
    try:
        print(f"[LOG] remove_from_portfolio called with user_id={user_id}, ticker={ticker}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to remove {ticker} from user {user_id}")
        
        pf = _pf(user_id)
        existed = ticker in pf
        
        if existed:
            pf.pop(ticker)
            print(f"[LOG] Successfully removed {ticker} from portfolio")
            return {
                "ok": True, 
                "message": f"Successfully removed {ticker} from portfolio",
                "removed": True, 
                "portfolio": pf,
                "portfolio_count": len(pf)
            }
        else:
            print(f"[LOG] Ticker {ticker} not found in portfolio")
            return {"ok": False, "error": f"Ticker {ticker} not found in portfolio"}
            
    except Exception as e:
        print(f"[LOG] Error removing from portfolio: {str(e)}")
        return {"ok": False, "error": f"Error removing from portfolio: {str(e)}"}

@tool("list_portfolio", args_schema=ListPortfolioInput)
def list_portfolio(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"):
    """List all holdings in the user's portfolio."""
    try:
        print(f"[LOG] list_portfolio called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        pf = _pf(user_id)
        
        print(f"[LOG] Successfully listed portfolio for user {user_id}")
        return {
            "ok": True,
            "portfolio": pf, 
            "portfolio_count": len(pf),
            "user_id": user_id
        }
        
    except Exception as e:
        print(f"[LOG] Error listing portfolio: {str(e)}")
        return {"ok": False, "error": f"Error listing portfolio: {str(e)}"}

@tool("add_to_watchlist", args_schema=AddWatchlistInput)
def add_to_watchlist(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = "",
                     note: Optional[str] = None):
    """Add a ticker to the user's watchlist by calling the watchlist API."""
    try:
        print(f"[LOG] add_to_watchlist called with user_id={user_id}, ticker={ticker}, note={note}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to add {ticker} for user {user_id}")
        
        # Make HTTP request to the watchlist API
        api_url = "http://localhost:8000/api/v1/watchlist/"
        payload = {
            "user_id": user_id,
            "ticker": ticker,
            "note": note
        }
        
        print(f"[LOG] API payload: {payload}")
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
        print(f"[LOG] API response status: {response.status_code}")
        print(f"[LOG] API response headers: {dict(response.headers)}")
        
        if response.status_code in [200, 201]:  # 200 OK, 201 Created
            result = response.json()
            print(f"[LOG] API response success: {result}")
            print(f"[LOG] Tool returning success response")
            return {
                "ok": True,
                "message": f"Successfully added {ticker} to watchlist",
                "api_response": result
            }
        elif response.status_code == 400:
            result = response.json()
            print(f"[LOG] API response error 400: {result}")
            print(f"[LOG] Tool returning error response for 400")
            return {"ok": False, "error": result.get("detail", "Unable to add ticker to watchlist")}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            print(f"[LOG] Tool returning error response for unexpected status")
            return {"ok": False, "error": "Unable to add ticker to watchlist at this time"}
            
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to add ticker to watchlist at this time"}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        print(f"[LOG] Tool returning error response for exception")
        return {"ok": False, "error": "Unable to add ticker to watchlist at this time"}

@tool("remove_from_watchlist", args_schema=RemoveWatchlistInput)
def remove_from_watchlist(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = ""):
    """Remove a ticker from the user's watchlist by calling the watchlist API."""
    try:
        print(f"[LOG] remove_from_watchlist called with user_id={user_id}, ticker={ticker}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        
        print(f"[LOG] Getting watchlist for user {user_id} to find entry for {ticker}")
        
        # First, get the watchlist to find the entry ID
        list_url = f"http://localhost:8000/api/v1/watchlist/?user_id={user_id}"
        list_response = requests.get(list_url)
        print(f"[LOG] List API response status: {list_response.status_code}")
        
        if list_response.status_code != 200:
            print(f"[LOG] Failed to get watchlist")
            return {"ok": False, "error": "Unable to remove ticker from watchlist"}
        
        list_data = list_response.json()
        entry_id = None
        
        # Find the entry with matching ticker
        for item in list_data.get("items", []):
            if item.get("ticker") == ticker:
                entry_id = item.get("id")
                break
        
        if not entry_id:
            print(f"[LOG] Entry not found for ticker {ticker}")
            return {"ok": False, "error": f"Ticker {ticker} not found in watchlist"}
        
        print(f"[LOG] Found entry ID {entry_id}, deleting...")
        
        # Delete the entry
        delete_url = f"http://localhost:8000/api/v1/watchlist/{entry_id}"
        delete_response = requests.delete(delete_url)
        print(f"[LOG] Delete API response status: {delete_response.status_code}")
        
        if delete_response.status_code == 200:
            print(f"[LOG] Successfully deleted entry {entry_id}")
            return {
                "ok": True,
                "message": f"Successfully removed {ticker} from watchlist"
            }
        else:
            print(f"[LOG] Failed to delete entry")
            return {"ok": False, "error": "Unable to remove ticker from watchlist"}
            
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to remove ticker from watchlist at this time"}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": "Unable to remove ticker from watchlist at this time"}

@tool("list_watchlist", args_schema=ListWatchlistInput)
def list_watchlist(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"):
    """List all tickers in the user's watchlist by calling the watchlist API."""
    try:
        print(f"[LOG] list_watchlist called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get watchlist for user {user_id}")
        
        # Make HTTP request to the watchlist API
        api_url = f"http://localhost:8000/api/v1/watchlist/?user_id={user_id}"
        response = requests.get(api_url)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success, found {result.get('total', 0)} items")
            return {
                "ok": True,
                "watchlist": result.get("items", []),
                "count": result.get("total", 0),
                "user_id": user_id
            }
        else:
            print(f"[LOG] API response failed")
            return {"ok": False, "error": "Unable to retrieve watchlist at this time"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to retrieve watchlist at this time"}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": "Unable to retrieve watchlist at this time"}

@tool("get_watchlist_entry", args_schema=ListWatchlistInput)
def get_watchlist_entry(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = ""):
    """Get a specific watchlist entry by ticker for a user by calling the watchlist API."""
    try:
        print(f"[LOG] get_watchlist_entry called with user_id={user_id}, ticker={ticker}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get watchlist for user {user_id}")
        
        # Make HTTP request to the watchlist API
        api_url = f"http://localhost:8000/api/v1/watchlist/?user_id={user_id}"
        response = requests.get(api_url)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Find the entry with matching ticker
            for item in result.get("items", []):
                if item.get("ticker") == ticker:
                    print(f"[LOG] Found entry for ticker {ticker}")
                    return {
                        "ok": True,
                        "entry": item,
                        "message": f"Found {ticker} in watchlist"
                    }
            
            print(f"[LOG] Entry not found for ticker {ticker}")
            return {
                "ok": False, 
                "error": f"Ticker {ticker} not found in watchlist",
                "user_id": user_id
            }
        else:
            print(f"[LOG] API response failed")
            return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}

@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str, max_results: int = 5):
    """Perform a web search for the given query."""
    return {
        "query": query,
        "results": [
            {
                "title": f"Test Result 1 for: {query}",
                "url": "https://example.com/result1",
                "snippet": f"This is a test snippet for the search query: {query}. This tool is working correctly!"
            },
            {
                "title": f"Test Result 2 for: {query}",
                "url": "https://example.com/result2",
                "snippet": f"Another test result showing that the web search tool is functioning properly for: {query}"
            }
        ],
        "total_results": 2,
        "status": "test_mode",
        "message": "This is a test implementation. Real web search API will be integrated later."
    }

@tool("get_news", args_schema=GetNewsInput)
def get_news(user_id: str = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", ticker: str = "", lookback_days: int = 3):
    """Fetch finance-focused news headlines for a given ticker within the last N days."""
    cache_key = f"news:{user_id}:{ticker}:{lookback_days}"
    if cache_key in DOC_CACHE:
        return DOC_CACHE[cache_key]
    
    mock_items = [
        {
            "ticker": ticker,
            "title": f"Mock News: {ticker} Reports Strong Q4 Earnings",
            "url": f"https://example.com/{ticker.lower()}-earnings",
            "source": "Mock Reuters",
            "snippet": f"This is a mock news snippet for {ticker} showing that the get_news tool is working correctly.",
            "published_at": "2024-01-15T10:30:00Z"
        },
        {
            "ticker": ticker,
            "title": f"Mock News: {ticker} Announces New Product Launch",
            "url": f"https://example.com/{ticker.lower()}-product",
            "source": "Mock Bloomberg",
            "snippet": f"Mock announcement from {ticker} about new product development.",
            "published_at": "2024-01-14T15:45:00Z"
        }
    ]
    
    result = {
        "ok": True,
        "ticker": ticker,
        "lookback_days": lookback_days,
        "items": mock_items,
        "status": "mock_mode",
        "message": "This is a mock implementation. Real Brave Search API will be integrated later."
    }
    DOC_CACHE[cache_key] = result
    return result

# ====== Tool Configuration ======
TOOLS = [
    add_to_portfolio,
    remove_from_portfolio,
    list_portfolio,
    add_to_watchlist,
    remove_from_watchlist,
    list_watchlist,
    get_watchlist_entry,
    web_search,
    get_news,
]

# ====== AI Agent Setup ======
SYSTEM_PROMPT = """You are Porta, a finance-focused assistant. Your job: manage a user's portfolio and watchlist.

Rules:
- Use tools to add/remove/list portfolio or watchlist.
- The watchlist tools call the external watchlist API to manage data.
- Check the "ok" field in tool responses - if it's False, there was an error.
- When operations fail, explain the error to the user clearly but simply.
- NEVER expose technical details, backend errors, or API connection issues to users.
- When operations succeed, provide a brief confirmation message with the result.
- If the user gives ambiguous instructions, ask a brief clarifying question.
- Be concise and neutral. Provide insights, not investment advice.
- Always respect ticker format (uppercase letters/numbers/.-).
- IMPORTANT: After successfully executing a tool, summarize the result and stop.

{agent_scratchpad}
"""

def build_agent():
    """Build the AI agent with proper error handling"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Put it in your environment or a .env file.")

    llm = ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219"),
        api_key=api_key,
        temperature=0,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=TOOLS, verbose=True)

# Global agent instance
agent_executor = None
agent_ready = False

def get_agent():
    """Get or create the global agent instance"""
    global agent_executor
    if agent_executor is None:
        agent_executor = build_agent()
    return agent_executor

# ====== FastAPI App ======
app = FastAPI(
    title="Porta Finance Assistant API",
    description="API for managing portfolios and watchlists with AI assistance",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Request Processing ======
def process_request_sync(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single request synchronously"""
    global ACTIVE_REQUESTS
    
    request_id = request_data["request_id"]
    message = request_data["message"]
    user_id = request_data["user_id"]
    chat_history = request_data["chat_history"]
    
    try:
        with REQUEST_LOCK:
            REQUEST_RESULTS[request_id]["status"] = "processing"
        
        # Get agent with error handling
        try:
            agent = get_agent()
        except Exception as e:
            error_msg = f"AI agent not ready: {str(e)}"
            with REQUEST_LOCK:
                REQUEST_RESULTS[request_id].update({
                    "status": "error",
                    "error": error_msg,
                    "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            return {"status": "error", "error": error_msg}
        
        # Convert chat history
        history = []
        for msg in chat_history:
            if msg.get("role") == "user":
                history.append({"role": "user", "content": msg.get("content", "")})
            elif msg.get("role") == "assistant":
                history.append({"role": "assistant", "content": msg.get("content", "")})
        
        # Invoke agent
        result = agent.invoke({
            "input": message,
            "chat_history": history
        })
        
        # Handle response format
        if isinstance(result, dict) and "output" in result:
            response_text = result["output"]
        elif isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                if "text" in first_item:
                    response_text = first_item["text"]
                elif "content" in first_item:
                    response_text = first_item["content"]
                else:
                    response_text = str(first_item)
            else:
                response_text = str(first_item)
        else:
            response_text = str(result)
        
        # Ensure response is string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Update results
        with REQUEST_LOCK:
            REQUEST_RESULTS[request_id].update({
                "status": "completed",
                "response": response_text,
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Cleanup old requests
            if len(REQUEST_RESULTS) > MAX_STORED_REQUESTS:
                old_requests = [
                    rid for rid, data in REQUEST_RESULTS.items()
                    if data["status"] in ["completed", "error"]
                ]
                if len(old_requests) > MAX_STORED_REQUESTS // 2:
                    for rid in old_requests[:len(old_requests) - MAX_STORED_REQUESTS // 2]:
                        REQUEST_RESULTS.pop(rid, None)
        
        return {"status": "success", "response": response_text}
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        print(f"Error in request {request_id}: {error_msg}")
        
        with REQUEST_LOCK:
            REQUEST_RESULTS[request_id].update({
                "status": "error",
                "error": error_msg,
                "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {"status": "error", "error": error_msg}

async def process_request_queue():
    """Background task to process queued requests"""
    global ACTIVE_REQUESTS
    
    while True:
        try:
            with REQUEST_LOCK:
                if ACTIVE_REQUESTS < MAX_CONCURRENT_REQUESTS and not REQUEST_QUEUE.empty():
                    request_data = REQUEST_QUEUE.get_nowait()
                    ACTIVE_REQUESTS += 1
                else:
                    await asyncio.sleep(0.1)
                    continue
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, process_request_sync, request_data)
            
            with REQUEST_LOCK:
                ACTIVE_REQUESTS -= 1
                
        except Exception as e:
            print(f"Error in request queue processor: {e}")
            await asyncio.sleep(1)

# ====== API Endpoints ======
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Porta Finance Assistant API", 
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        with REQUEST_LOCK:
            queue_size = REQUEST_QUEUE.qsize()
            active_requests = ACTIVE_REQUESTS
            
        return {
            "status": "healthy",
            "agent_ready": agent_ready,
            "tools_available": len(TOOLS),
            "tool_names": [tool.name for tool in TOOLS],
            "async_processing": {
                "queue_size": queue_size,
                "active_requests": active_requests,
                "max_concurrent": MAX_CONCURRENT_REQUESTS
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Send a message to the Porta finance assistant"""
    try:
        # Try to get agent with error handling
        try:
            agent = get_agent()
        except Exception as e:
            return ChatResponse(
                response=f"AI agent not ready yet. Please try again in a moment. Error: {str(e)}",
                user_id=request.user_id,
                status="agent_not_ready"
            )
        
        # Convert chat history
        history = []
        for msg in request.chat_history:
            if msg.get("role") == "user":
                history.append({"role": "user", "content": msg.get("content", "")})
            elif msg.get("role") == "assistant":
                history.append({"role": "assistant", "content": msg.get("content", "")})
        
        # Invoke agent
        result = agent.invoke({
            "input": request.message,
            "chat_history": history
        })
        
        # Handle response format
        if isinstance(result, dict) and "output" in result:
            response_text = result["output"]
        elif isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if isinstance(first_item, dict):
                if "text" in first_item:
                    response_text = first_item["text"]
                elif "content" in first_item:
                    response_text = first_item["content"]
                else:
                    response_text = str(first_item)
            else:
                response_text = str(first_item)
        else:
            response_text = str(result)
        
        # Ensure response is string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/chat/async", response_model=AsyncChatResponse)
async def chat_with_agent_async(request: AsyncChatRequest):
    """Send a message to the Porta finance assistant (asynchronous)"""
    try:
        request_id = str(uuid.uuid4())
        
        request_data = {
            "request_id": request_id,
            "message": request.message,
            "user_id": request.user_id,
            "chat_history": request.chat_history
        }
        
        with REQUEST_LOCK:
            REQUEST_RESULTS[request_id] = {
                "request_id": request_id,
                "status": "queued",
                "response": None,
                "user_id": request.user_id,
                "error": None,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": None
            }
        
        REQUEST_QUEUE.put(request_data)
        
        return AsyncChatResponse(
            request_id=request_id,
            status="queued",
            message="Request queued for processing"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing request: {str(e)}")

@app.get("/chat/status/{request_id}", response_model=RequestStatusResponse)
async def get_request_status(request_id: str):
    """Get the status and result of an async request"""
    try:
        with REQUEST_LOCK:
            if request_id not in REQUEST_RESULTS:
                raise HTTPException(status_code=404, detail="Request not found")
            
            result = REQUEST_RESULTS[request_id]
            return RequestStatusResponse(**result)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving request status: {str(e)}")

@app.get("/chat/requests")
async def list_active_requests():
    """List all active and recent requests"""
    try:
        with REQUEST_LOCK:
            return {
                "active_requests": ACTIVE_REQUESTS,
                "queue_size": REQUEST_QUEUE.qsize(),
                "recent_requests": list(REQUEST_RESULTS.values())[-10:]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing requests: {str(e)}")

@app.get("/portfolio/{user_id}")
async def get_user_portfolio(user_id: str):
    """Get user's portfolio"""
    return {"portfolio": _pf(user_id), "user_id": user_id}

@app.get("/watchlist/{user_id}")
async def get_user_watchlist(user_id: str):
    """Get user's watchlist"""
    return {"watchlist": sorted(_wl(user_id).values()), "user_id": user_id}


# ====== Interactive Mode ======
def run_interactive():
    """Run the agent in interactive mode"""
    agent = build_agent()
    print("=== Welcome to Porta - Your Finance Assistant ===")
    print("I can help you manage your portfolio and watchlist!")
    print("Example commands:")
    print("  - 'add AAPL to my watchlist'")
    print("  - 'put MSFT in my portfolio'")
    print("  - 'list my portfolio'")
    print("  - 'remove AAPL from watchlist'")
    print("  - 'get watchlist entry for AAPL'")
    print("  - 'search for Tesla stock news'")
    print("  - 'web search for market trends'")
    print("  - 'get news for AAPL'")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 50)

    history: List[dict] = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye! 👋")
                break
            if not user_input:
                continue

            print("Porta: ", end="", flush=True)
            
            result = agent.invoke({"input": user_input, "chat_history": history})
            
            print(result["output"])
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": result})

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.")

def test_watchlist_tool():
    """Test the watchlist tool directly to debug the issue"""
    print("=== Testing Watchlist Tool ===")
    
    # Test the underlying function directly (not the LangChain tool wrapper)
    print("Testing add_to_watchlist function...")
    
    # Import the requests module to test the API call
    import requests
    
    user_id = "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"
    ticker = "TEST"
    note = "Test entry"
    
    print(f"Testing API call with: user_id={user_id}, ticker={ticker}, note={note}")
    
    try:
        # Make the same API call that the tool makes
        api_url = "http://localhost:8000/api/v1/watchlist/"
        payload = {
            "user_id": user_id,
            "ticker": ticker,
            "note": note
        }
        
        print(f"Making POST request to: {api_url}")
        print(f"Payload: {payload}")
        
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code in [200, 201]:  # 200 OK, 201 Created
            result = response.json()
            print(f"✅ API call successful: {result}")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            try:
                error_result = response.json()
                print(f"Error details: {error_result}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - API server not running on port 8000")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
    
    print("=== Test Complete ===")

# ====== Main Entry Point ======
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            run_interactive()
        else:
            print("Usage: python agent.py [interactive]")
            print("Default: Runs FastAPI server")
    else:
        # Start background task for request processing
        @app.on_event("startup")
        async def startup_event():
            """Initialize background tasks on startup"""
            print("✅ Porta Finance Assistant API is ready!")
            asyncio.create_task(process_request_queue())
            print("✅ Async request processor started!")
            
            # Initialize agent in background
            async def init_agent():
                global agent_ready
                try:
                    print("🔄 Initializing AI agent in background...")
                    agent = await asyncio.get_event_loop().run_in_executor(None, get_agent)
                    agent_ready = True
                    print("✅ AI agent initialized successfully!")
                except Exception as e:
                    print(f"❌ Failed to initialize agent: {e}")
                    print("⚠️  AI features may not work")
            
            asyncio.create_task(init_agent())
        
        print("🚀 Starting Porta Finance Assistant API...")
        print("✅ Async processing enabled - supports multiple concurrent requests!")
        uvicorn.run(
            "agent:app", 
            host="127.0.0.1", 
            port=8001, 
            reload=False,
            log_level="info"
        )
