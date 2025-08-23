import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, constr # type: ignore

# LangChain core + Anthropic
from langchain_anthropic import ChatAnthropic # type: ignore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # type: ignore
from langchain_core.tools import tool # type: ignore
from langchain.agents import AgentExecutor, create_tool_calling_agent # type: ignore        
from langchain_core.callbacks import BaseCallbackHandler # type: ignore

# ====== In-memory stores ======
PORTFOLIO: Dict[str, Dict[str, Dict[str, Any]]] = {}  # user_id -> {ticker: {"weight":float|None,"note":str|None}}
WATCHLIST: Dict[str, set] = {}                         # user_id -> set(tickers)
DOC_CACHE: Dict[str, Any] = {}                         # Cache for various document types including news


def _pf(user_id: str) -> Dict[str, Dict[str, Any]]:
    return PORTFOLIO.setdefault(user_id, {})


def _wl(user_id: str) -> set:
    return WATCHLIST.setdefault(user_id, set())


Ticker = constr(pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")

# ====== Tool input schemas ======
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
    lookback_days: int = Field(default=3, ge=1, le=30,
                               description="Number of days to look back for news")


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

# ====== Web Search Tool ======
class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to perform web search for")
    max_results: Optional[int] = Field(default=5,
                                       description="Maximum number of results to return")


@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str, max_results: int = 5):
    """Perform a web search for the given query. This is a test implementation that will be replaced with actual API integration later."""

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
    
    # Check cache first
    cache_key = f"news:{user_id}:{ticker}:{lookback_days}"
    if cache_key in DOC_CACHE:
        return DOC_CACHE[cache_key]
    
    # Mock response for testing tool calling
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
        },
        {
            "ticker": ticker,
            "title": f"Mock News: {ticker} Stock Analysis and Outlook",
            "url": f"https://example.com/{ticker.lower()}-analysis",
            "source": "Mock CNBC",
            "snippet": f"Mock financial analysis and future outlook for {ticker} stock.",
            "published_at": "2024-01-13T09:15:00Z"
        }
    ]
    
    # Cache the results
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

# Create a dictionary mapping tool names to tool functions for easy lookup
TOOLS_DICT = {tool.name: tool for tool in TOOLS}

# Custom callback to show tool calls
class ToolCallCallback(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"\n🔧 TOOL CALLED: {serialized['name']}")
        print(f"   Input: {input_str}")
    
    def on_tool_end(self, output, **kwargs):
        print(f"   Output: {output}")
    
    def on_tool_error(self, error, **kwargs):
        print(f"   Error: {error}")


SYSTEM = """You are Porta, a finance-focused assistant. Your job: manage a user's portfolio and watchlist.

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
    """Build a proper agent executor that can call tools"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Put it in your environment or a .env file.")

    llm = ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219"),
        api_key=api_key,
        temperature=0,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=True)
    
    return agent_executor


def run_interactive():
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
    print("  - 'get news for MSFT last 7 days'")
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


def test_tool_calls():
    """Test function to quickly verify tool calls"""
    print("Testing tool calls...")
    agent = build_agent()
    
    test_queries = [
        "add AAPL to my watchlist",
        "put MSFT in my portfolio",
        "list my portfolio",
        "search for Tesla stock news",
        "get news for AAPL"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing: {query}")
        print('='*50)
        
        result = agent.invoke({"input": query, "chat_history": []})
        
        print(f"\nResponse: {result['output']}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_tool_calls()
    else:
        run_interactive()
