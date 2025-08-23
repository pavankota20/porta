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
    user_id: str = Field(default="demo_user")
    ticker: Ticker
    weight: Optional[float] = None
    note: Optional[str] = None

class RemovePortfolioInput(BaseModel):
    user_id: str = Field(default="demo_user")
    ticker: Ticker

class ListPortfolioInput(BaseModel):
    user_id: str = Field(default="demo_user")

class AddWatchlistInput(BaseModel):
    user_id: str = Field(default="demo_user")
    ticker: Ticker
    note: Optional[str] = None

class RemoveWatchlistInput(BaseModel):
    user_id: str = Field(default="demo_user")
    ticker: Ticker

class ListWatchlistInput(BaseModel):
    user_id: str = Field(default="demo_user")

class GetNewsInput(BaseModel):
    user_id: str = Field(default="demo_user")
    ticker: Ticker
    lookback_days: int = Field(default=3, ge=1, le=30)

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to perform web search for")
    max_results: Optional[int] = Field(default=5, description="Maximum number of results to return")

# ====== API Models ======
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/prompt")
    user_id: str = Field(default="demo_user", description="User identifier")
    chat_history: List[Dict[str, str]] = Field(default=[], description="Previous chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(default="success", description="Response status")

class AsyncChatRequest(BaseModel):
    message: str = Field(..., description="User's message/prompt")
    user_id: str = Field(default="demo_user", description="User identifier")
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

# ====== Data Storage ======
PORTFOLIO: Dict[str, Dict[str, Dict[str, Any]]] = {}
WATCHLIST: Dict[str, set] = {}
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

def _wl(user_id: str) -> set:
    """Get user watchlist, create if doesn't exist"""
    return WATCHLIST.setdefault(user_id, set())

# ====== LangChain Tools ======
@tool("add_to_portfolio", args_schema=AddPortfolioInput)
def add_to_portfolio(user_id: str = "demo_user", ticker: str = "",
                     weight: Optional[float] = None, note: Optional[str] = None):
    """Add or upsert a holding in the user's portfolio."""
    pf = _pf(user_id)
    pf[ticker] = {"weight": weight, "note": note}
    return {"ok": True, "portfolio": pf}

@tool("remove_from_portfolio", args_schema=RemovePortfolioInput)
def remove_from_portfolio(user_id: str = "demo_user", ticker: str = ""):
    """Remove a holding from the user's portfolio."""
    pf = _pf(user_id)
    existed = ticker in pf
    pf.pop(ticker, None)
    return {"ok": True, "removed": existed, "portfolio": pf}

@tool("list_portfolio", args_schema=ListPortfolioInput)
def list_portfolio(user_id: str = "demo_user"):
    """List all holdings in the user's portfolio."""
    return {"portfolio": _pf(user_id)}

@tool("add_to_watchlist", args_schema=AddWatchlistInput)
def add_to_watchlist(user_id: str = "demo_user", ticker: str = "",
                     note: Optional[str] = None):
    """Add a ticker to the user's watchlist."""
    wl = _wl(user_id)
    wl.add(ticker)
    return {"ok": True, "watchlist": sorted(wl)}

@tool("remove_from_watchlist", args_schema=RemoveWatchlistInput)
def remove_from_watchlist(user_id: str = "demo_user", ticker: str = ""):
    """Remove a ticker from the user's watchlist."""
    wl = _wl(user_id)
    existed = ticker in wl
    wl.discard(ticker)
    return {"ok": True, "removed": existed, "watchlist": sorted(wl)}

@tool("list_watchlist", args_schema=ListWatchlistInput)
def list_watchlist(user_id: str = "demo_user"):
    """List all tickers in the user's watchlist."""
    return {"watchlist": sorted(_wl(user_id))}

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
def get_news(user_id: str = "demo_user", ticker: str = "", lookback_days: int = 3):
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
    web_search,
    get_news,
]

# ====== AI Agent Setup ======
SYSTEM_PROMPT = """You are Porta, a finance-focused assistant. Your job: manage a user's portfolio and watchlist.

Rules:
- Use tools to add/remove/list portfolio or watchlist.
- After calling a tool, provide a brief confirmation message to the user.
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
    return {"watchlist": sorted(_wl(user_id)), "user_id": user_id}

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
            port=8000, 
            reload=False,
            log_level="info"
        )
