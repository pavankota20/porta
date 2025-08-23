#!/usr/bin/env python3
"""
Porta Finance Assistant API
A FastAPI-based financial portfolio and watchlist management system with AI assistance.
"""

import os
import sys
import asyncio
from typing import List
import uvicorn # type: ignore
from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.exceptions import HTTPException # type: ignore

# LangChain imports
from langchain_anthropic import ChatAnthropic # type: ignore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # type: ignore
from langchain.agents import create_tool_calling_agent, AgentExecutor # type: ignore

# Local imports
from config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL, SYSTEM_PROMPT, 
    HOST, PORT, MAX_CONCURRENT_REQUESTS
)
from models import (
    ChatRequest, ChatResponse, AsyncChatRequest, AsyncChatResponse,
    RequestStatusResponse, WebSearchInput
)
from tools import TOOLS
from api_routes import (
    root, health_check, chat_with_agent, chat_with_agent_async,
    get_request_status, list_active_requests, get_user_sessions, get_session_messages, close_chat_session
)
from request_processor import process_request_queue

# ====== AI Agent Setup ======
def build_agent():
    """Build the AI agent with proper error handling"""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Put it in your environment or a .env file.")

    llm = ChatAnthropic(
        model=ANTHROPIC_MODEL,
        api_key=ANTHROPIC_API_KEY,
        temperature=0,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(
        agent=agent, 
        tools=TOOLS, 
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )

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

# ====== API Endpoints ======
@app.get("/")
async def api_root():
    return await root()

@app.get("/health")
async def api_health_check():
    return await health_check()

@app.post("/chat", response_model=ChatResponse)
async def api_chat_with_agent(request: ChatRequest):
    return await chat_with_agent(request)

@app.post("/chat/async", response_model=AsyncChatResponse)
async def api_chat_with_agent_async(request: AsyncChatRequest):
    return await chat_with_agent_async(request)

@app.post("/api/v1/web-search/")
async def api_web_search(request: WebSearchInput):
    """Web search endpoint that integrates with Brave Search API"""
    try:
        print(f"[LOG] Web search request: {request}")
        
        # Check if Brave Search API key is configured
        from config import BRAVE_SEARCH_API_KEY, BRAVE_SEARCH_BASE_URL
        
        if not BRAVE_SEARCH_API_KEY:
            raise HTTPException(
                status_code=500, 
                detail="Brave Search API key not configured. Please set BRAVE_SEARCH_API_KEY in your .env file."
            )
        
        # Prepare the request to Brave Search API
        import aiohttp
        
        brave_payload = {
            "q": request.query,
            "count": request.count,
            "offset": request.offset,
            "search_lang": request.search_lang,
            "country": request.country,
            "ui_lang": request.ui_lang,
            "safesearch": request.safesearch
        }
        
        # Add result filter if specified
        if request.result_filter and request.result_filter != "web":
            brave_payload["result_filter"] = request.result_filter
        
        print(f"[LOG] Making request to Brave Search API: {brave_payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                BRAVE_SEARCH_BASE_URL,
                params=brave_payload,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
                    "User-Agent": "Porta-Finance-Assistant/1.0"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                print(f"[LOG] Brave Search API response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"[LOG] Brave Search API response success")
                    return result
                elif response.status == 401:
                    raise HTTPException(
                        status_code=401, 
                        detail="Brave Search API authentication failed. Please check your API key."
                    )
                elif response.status == 429:
                    raise HTTPException(
                        status_code=429, 
                        detail="Brave Search API rate limit exceeded. Please try again later."
                    )
                elif response.status == 400:
                    error_detail = await response.json()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid search request: {error_detail.get('message', 'Unknown error')}"
                    )
                else:
                    error_detail = await response.text()
                    raise HTTPException(
                        status_code=502, 
                        detail=f"Brave Search API error (HTTP {response.status}): {error_detail}"
                    )
                    
    except HTTPException:
        raise
    except aiohttp.ClientConnectorError:
        raise HTTPException(
            status_code=502, 
            detail="Unable to connect to Brave Search API. Please check your internet connection."
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, 
            detail="Brave Search API request timed out. Please try again."
        )
    except Exception as e:
        print(f"[ERROR] Web search error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error during web search: {str(e)}"
        )

@app.get("/chat/status/{request_id}", response_model=RequestStatusResponse)
async def api_get_request_status(request_id: str):
    return await get_request_status(request_id)

@app.get("/chat/requests")
async def api_list_active_requests():
    return await list_active_requests()

@app.get("/sessions/{user_id}")
async def api_get_user_sessions(user_id: str):
    return await get_user_sessions(user_id)

@app.get("/sessions/{session_id}/messages")
async def api_get_session_messages(session_id: str, user_id: str):
    return await get_session_messages(session_id, user_id)

@app.delete("/sessions/{session_id}")
async def api_close_chat_session(session_id: str, user_id: str):
    return await close_chat_session(session_id, user_id)

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
    import requests # type: ignore
    from config import DEFAULT_USER_ID, WATCHLIST_API_URL
    
    user_id = DEFAULT_USER_ID
    ticker = "TEST"
    note = "Test entry"
    
    print(f"Testing API call with: user_id={user_id}, ticker={ticker}, note={note}")
    
    try:
        # Make the same API call that the tool makes
        payload = {
            "user_id": user_id,
            "ticker": ticker,
            "note": note
        }
        
        print(f"Making POST request to: {WATCHLIST_API_URL}")
        print(f"Payload: {payload}")
        
        response = requests.post(WATCHLIST_API_URL, json=payload, headers={"Content-Type": "application/json"})
        
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
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            run_interactive()
        elif sys.argv[1] == "test":
            test_watchlist_tool()
        else:
            print("Usage: python agent.py [interactive|test]")
            print("Default: Runs FastAPI server")
    else:
        # Start background task for request processing
        @app.on_event("startup")
        async def startup_event():
            """Initialize background tasks on startup"""
            print("✅ Porta Finance Assistant API is ready!")
            
            # Initialize database service
            try:
                from database import init_db
                await init_db()
                print("✅ Database service initialized!")
            except Exception as e:
                print(f"❌ Failed to initialize database: {e}")
                print("⚠️  Chat sessions and messages may not work")
            
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
        
        @app.on_event("shutdown")
        async def shutdown_event():
            """Cleanup on shutdown"""
            try:
                from database import cleanup_db
                await cleanup_db()
                print("✅ Database service cleaned up!")
            except Exception as e:
                print(f"⚠️  Error during database cleanup: {e}")
        
        print("🚀 Starting Porta Finance Assistant API...")
        print("✅ Async processing enabled - supports multiple concurrent requests!")
        uvicorn.run(
            "agent:app", 
            host=HOST, 
            port=PORT, 
            reload=False,
            log_level="info"
        )
