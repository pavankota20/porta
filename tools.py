#!/usr/bin/env python3
"""
LangChain tools for Porta Finance Assistant
"""

from typing import Optional
from langchain_core.tools import tool # type: ignore
import requests # type: ignore
import json

from config import DEFAULT_USER_ID, DOC_CACHE, WATCHLIST_API_URL, PORTFOLIO_API_URL
from models import (
    AddPortfolioInput, RemovePortfolioInput, ListPortfolioInput, GetPortfolioSummaryInput,
    AddWatchlistInput, RemoveWatchlistInput, ListWatchlistInput, GetWatchlistEntryInput,
    GetNewsInput, WebSearchInput
)

# ====== Helper Functions ======
# Database functions are now handled by database.py service

# ====== Portfolio Tools ======
@tool("add_to_portfolio", args_schema=AddPortfolioInput)
def add_to_portfolio(user_id: str = DEFAULT_USER_ID, ticker: str = "",
                     quantity: str = "", buy_price: str = "", note: Optional[str] = None):
    """Add or upsert a holding in the user's portfolio by calling the portfolio API."""
    try:
        print(f"[LOG] add_to_portfolio called with user_id={user_id}, ticker={ticker}, quantity={quantity}, buy_price={buy_price}, note={note}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            print(f"[LOG] Validation failed: ticker is empty")
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        if not quantity or not quantity.strip():
            print(f"[LOG] Validation failed: quantity is empty")
            return {"ok": False, "error": "Quantity cannot be empty. Please specify the number of shares."}
        
        if not buy_price or not buy_price.strip():
            print(f"[LOG] Validation failed: buy_price is empty")
            return {"ok": False, "error": "Buy price cannot be empty. Please specify the purchase price per share."}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        quantity = quantity.strip()
        buy_price = buy_price.strip()
        
        # Validate quantity format (should be a positive number)
        try:
            qty_float = float(quantity)
            if qty_float <= 0:
                print(f"[LOG] Validation failed: quantity must be positive ({quantity})")
                return {"ok": False, "error": "Quantity must be a positive number"}
        except ValueError:
            print(f"[LOG] Validation failed: quantity is not a valid number ({quantity})")
            return {"ok": False, "error": "Quantity must be a valid number"}
        
        # Validate buy_price format (should be a positive number)
        try:
            price_float = float(buy_price)
            if price_float <= 0:
                print(f"[LOG] Validation failed: buy_price must be positive ({buy_price})")
                return {"ok": False, "error": "Buy price must be a positive number"}
        except ValueError:
            print(f"[LOG] Validation failed: buy_price is not a valid number ({buy_price})")
            return {"ok": False, "error": "Buy price must be a valid number"}
        
        print(f"[LOG] Making API request to add {ticker} to portfolio for user {user_id}")
        
        # Make HTTP request to the portfolio API
        payload = {
            "user_id": user_id,
            "ticker": ticker,
            "quantity": quantity,
            "buy_price": buy_price,
            "note": note
        }
        
        print(f"[LOG] API payload: {payload}")
        response = requests.post(PORTFOLIO_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code in [200, 201]:  # 200 OK, 201 Created
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "message": f"Successfully added {ticker} to portfolio",
                "api_response": result
            }
        elif response.status_code == 400:
            result = response.json()
            print(f"[LOG] API response error 400: {result}")
            return {"ok": False, "error": result.get("detail", "Unable to add ticker to portfolio")}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            return {"ok": False, "error": "Unable to add ticker to portfolio at this time"}
            
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to portfolio service. Please check if the service is running."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error adding to portfolio: {str(e)}"}

@tool("remove_from_portfolio", args_schema=RemovePortfolioInput)
def remove_from_portfolio(user_id: str = DEFAULT_USER_ID, ticker: str = ""):
    """Remove a holding from the user's portfolio by calling the portfolio API."""
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
        
        print(f"[LOG] Getting portfolio for user {user_id} to find entry for {ticker}")
        
        # First, get the portfolio to find the entry ID
        list_url = f"{PORTFOLIO_API_URL}?user_id={user_id}&ticker={ticker}"
        list_response = requests.get(list_url, timeout=10)
        print(f"[LOG] List API response status: {list_response.status_code}")
        
        if list_response.status_code != 200:
            print(f"[LOG] Failed to get portfolio")
            return {"ok": False, "error": "Unable to remove ticker from portfolio"}
        
        list_data = list_response.json()
        entry_id = None
        
        # Find the entry with matching ticker - handle both "portfolios" and "items" fields
        items = list_data.get("items", list_data.get("portfolios", []))
        for item in items:
            if item.get("ticker") == ticker:
                entry_id = item.get("id") or item.get("portfolio_id")
                break
        
        if not entry_id:
            print(f"[LOG] Entry not found for ticker {ticker}")
            return {"ok": False, "error": f"Ticker {ticker} not found in portfolio"}
        
        print(f"[LOG] Found entry ID {entry_id}, deleting...")
        
        # Delete the entry
        delete_url = f"{PORTFOLIO_API_URL.rstrip('/')}/{entry_id}"
        delete_response = requests.delete(delete_url, timeout=10)
        print(f"[LOG] Delete API response status: {delete_response.status_code}")
        
        if delete_response.status_code == 200:
            print(f"[LOG] Successfully deleted entry {entry_id}")
            return {
                "ok": True,
                "message": f"Successfully removed {ticker} from portfolio"
            }
        else:
            print(f"[LOG] Failed to delete entry")
            return {"ok": False, "error": "Unable to remove ticker from portfolio"}
            
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to portfolio service. Please check if the service is running."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error removing from portfolio: {str(e)}"}

@tool("list_portfolio", args_schema=ListPortfolioInput)
def list_portfolio(user_id: str = DEFAULT_USER_ID):
    """List all holdings in the user's portfolio by calling the portfolio API."""
    try:
        print(f"[LOG] list_portfolio called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get portfolio for user {user_id}")
        
        # Make HTTP request to the portfolio API
        api_url = f"{PORTFOLIO_API_URL}?user_id={user_id}"
        response = requests.get(api_url, timeout=10)  # 10 second timeout
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response: {result}")
            
            # Validate the response structure - handle both "items" and "portfolios" fields
            items = result.get("items", result.get("portfolios", []))
            total_count = result.get("total", 0)
            
            # Check for data inconsistency
            if total_count > 0 and (not items or len(items) == 0):
                print(f"[LOG] Data inconsistency detected: total={total_count}, items={len(items) if items else 0}")
                return {
                    "ok": False,
                    "error": f"Data inconsistency detected: API reports {total_count} items but returned empty list. This may be a temporary issue with the portfolio service.",
                    "user_id": user_id,
                    "api_total": total_count,
                    "api_items_count": len(items) if items else 0
                }
            
            print(f"[LOG] API response success, found {len(items)} items")
            return {
                "ok": True,
                "portfolio": items,
                "portfolio_count": len(items),
                "user_id": user_id
            }
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"[LOG] API error detail: {error_detail}")
                return {"ok": False, "error": f"Portfolio API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve portfolio (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to portfolio service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Portfolio service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving portfolio: {str(e)}"}

@tool("get_portfolio_summary", args_schema=GetPortfolioSummaryInput)
def get_portfolio_summary(user_id: str = DEFAULT_USER_ID, include_pnl: bool = True):
    """Get portfolio summary with PnL calculations for a user by calling the portfolio API."""
    try:
        print(f"[LOG] get_portfolio_summary called with user_id={user_id}, include_pnl={include_pnl}")
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get portfolio summary for user {user_id}")
        
        # Make HTTP request to the portfolio summary API
        api_url = f"{PORTFOLIO_API_URL}summary/{user_id}?include_pnl={str(include_pnl).lower()}"
        response = requests.get(api_url, timeout=10)  # 10 second timeout
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "summary": result,
                "user_id": user_id,
                "include_pnl": include_pnl
            }
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"[LOG] API error detail: {error_detail}")
                return {"ok": False, "error": f"Portfolio summary API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve portfolio summary (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to portfolio service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Portfolio service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving portfolio summary: {str(e)}"}

# ====== Watchlist Tools ======
@tool("add_to_watchlist", args_schema=AddWatchlistInput)
def add_to_watchlist(user_id: str = DEFAULT_USER_ID, ticker: str = "",
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
        payload = {
            "user_id": user_id,
            "ticker": ticker,
            "note": note
        }
        
        print(f"[LOG] API payload: {payload}")
        response = requests.post(WATCHLIST_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
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
        return {"ok": False, "error": "Unable to connect to watchlist service. Please check if the service is running."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error adding to watchlist: {str(e)}"}

@tool("remove_from_watchlist", args_schema=RemoveWatchlistInput)
def remove_from_watchlist(user_id: str = DEFAULT_USER_ID, ticker: str = ""):
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
        list_url = f"{WATCHLIST_API_URL}?user_id={user_id}"
        list_response = requests.get(list_url, timeout=10)
        print(f"[LOG] List API response status: {list_response.status_code}")
        
        if list_response.status_code != 200:
            print(f"[LOG] Failed to get watchlist")
            return {"ok": False, "error": "Unable to remove ticker from watchlist"}
        
        list_data = list_response.json()
        entry_id = None
        
        # Find the entry with matching ticker - handle both "items" and "watchlists" fields
        items = list_data.get("items", list_data.get("watchlists", []))
        for item in items:
            if item.get("ticker") == ticker:
                entry_id = item.get("id") or item.get("watchlist_id")
                break
        
        if not entry_id:
            print(f"[LOG] Entry not found for ticker {ticker}")
            return {"ok": False, "error": f"Ticker {ticker} not found in watchlist"}
        
        print(f"[LOG] Found entry ID {entry_id}, deleting...")
        
        # Delete the entry
        delete_url = f"{WATCHLIST_API_URL.rstrip('/')}/{entry_id}"
        delete_response = requests.delete(delete_url, timeout=10)
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
def list_watchlist(user_id: str = DEFAULT_USER_ID):
    """List all tickers in the user's watchlist by calling the watchlist API."""
    try:
        print(f"[LOG] list_watchlist called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            print(f"[LOG] Validation failed: user_id is empty")
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get watchlist for user {user_id}")
        
        # Make HTTP request to the watchlist API
        api_url = f"{WATCHLIST_API_URL}?user_id={user_id}"
        response = requests.get(api_url, timeout=10)  # 10 second timeout
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response: {result}")
            
            # Validate the response structure - handle both "items" and "watchlists" fields
            items = result.get("items", result.get("watchlists", []))
            total_count = result.get("total", 0)
            
            # Check for data inconsistency
            if total_count > 0 and (not items or len(items) == 0):
                print(f"[LOG] Data inconsistency detected: total={total_count}, items={len(items) if items else 0}")
                return {
                    "ok": False,
                    "error": f"Data inconsistency detected: API reports {total_count} items but returned empty list. This may be a temporary issue with the watchlist service.",
                    "user_id": user_id,
                    "api_total": total_count,
                    "api_items_count": len(items) if items else 0
                }
            
            print(f"[LOG] API response success, found {len(items)} items")
            return {
                "ok": True,
                "watchlist": items,
                "count": len(items),
                "user_id": user_id
            }
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"[LOG] API error detail: {error_detail}")
                return {"ok": False, "error": f"Watchlist API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve watchlist (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to watchlist service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Watchlist service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving watchlist: {str(e)}"}

@tool("get_watchlist_entry", args_schema=GetWatchlistEntryInput)
def get_watchlist_entry(user_id: str = DEFAULT_USER_ID, ticker: str = ""):
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
        api_url = f"{WATCHLIST_API_URL}?user_id={user_id}"
        response = requests.get(api_url, timeout=10)  # 10 second timeout
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response: {result}")
            
            # Validate the response structure - handle both "items" and "watchlists" fields
            items = result.get("items", result.get("watchlists", []))
            total_count = result.get("total", 0)
            
            # Check for data inconsistency
            if total_count > 0 and (not items or len(items) == 0):
                print(f"[LOG] Data inconsistency detected: total={total_count}, items={len(items) if items else 0}")
                return {
                    "ok": False,
                    "error": f"Data inconsistency detected: API reports {total_count} items but returned empty list. This may be a temporary issue with the watchlist service.",
                    "user_id": user_id,
                    "api_total": total_count,
                    "api_items_count": len(items) if items else 0
                }
            
            # Find the entry with matching ticker
            for item in items:
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
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"[LOG] API error detail: {error_detail}")
                return {"ok": False, "error": f"Watchlist API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve watchlist entry (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}

# ====== Other Tools ======
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
def get_news(user_id: str = DEFAULT_USER_ID, ticker: str = "", lookback_days: int = 3):
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

# ====== Tool List ======
TOOLS = [
    add_to_portfolio,
    remove_from_portfolio,
    list_portfolio,
    get_portfolio_summary,
    add_to_watchlist,
    remove_from_watchlist,
    list_watchlist,
    get_watchlist_entry,
    web_search,
    get_news,
]
