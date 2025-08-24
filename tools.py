#!/usr/bin/env python3
"""
Simple sync LangChain tools for Porta Finance Assistant
"""

from typing import Optional, List, Dict, Any
from langchain.tools import tool # type: ignore
import requests

from config import DEFAULT_USER_ID, DOC_CACHE, WATCHLIST_API_URL, PORTFOLIO_API_URL, WEB_SEARCH_API_URL, USER_PREFERENCES_API_URL, USER_INTERACTIONS_API_URL, PREFERENCE_HISTORY_API_URL
from models import (
    AddPortfolioInput, RemovePortfolioInput, ListPortfolioInput, GetPortfolioSummaryInput,
    AddWatchlistInput, RemoveWatchlistInput, ListWatchlistInput, GetWatchlistEntryInput,
    WebSearchInput, StressTestInput, UserPreferencesInput, GetUserPreferencesInput, 
    ListUserPreferencesInput, UserInteractionInput, GetUserInteractionsInput, GetPreferenceHistoryInput
)

# ====== Portfolio Tools ======
@tool("add_to_portfolio", args_schema=AddPortfolioInput)
def add_to_portfolio(user_id: str = DEFAULT_USER_ID, ticker: str = "",
                     quantity: str = "", buy_price: str = "", note: Optional[str] = None):
    """Add or upsert a holding in the user's portfolio by calling the portfolio API."""
    try:
        print(f"[LOG] add_to_portfolio called with user_id={user_id}, ticker={ticker}, quantity={quantity}, buy_price={buy_price}, note={note}")
        
        # Validate inputs
        if not ticker or not ticker.strip():
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        if not quantity or not quantity.strip():
            return {"ok": False, "error": "Quantity cannot be empty. Please specify the number of shares."}
        
        if not buy_price or not buy_price.strip():
            return {"ok": False, "error": "Buy price cannot be empty. Please specify the purchase price per share."}
        
        ticker = ticker.strip().upper()
        user_id = user_id.strip()
        quantity = quantity.strip()
        buy_price = buy_price.strip()
        
        # Validate quantity format (should be a positive number)
        try:
            qty_float = float(quantity)
            if qty_float <= 0:
                return {"ok": False, "error": "Quantity must be a positive number"}
        except ValueError:
            return {"ok": False, "error": "Quantity must be a valid number"}
        
        # Validate buy_price format (should be a positive number)
        try:
            price_float = float(buy_price)
            if price_float <= 0:
                return {"ok": False, "error": "Buy price must be a positive number"}
        except ValueError:
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
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Portfolio service request timed out. Please try again."}
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
            return {"ok": False, "error": "Ticker cannot be empty"}
        
        if not user_id or not user_id.strip():
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
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Portfolio service request timed out. Please try again."}
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
        
        response = requests.get(api_url, timeout=10)
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
        
        response = requests.get(api_url, timeout=10)
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
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Watchlist service request timed out. Please try again."}
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
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Watchlist service request timed out. Please try again."}
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
        
        response = requests.get(api_url, timeout=10)
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
        
        response = requests.get(api_url, timeout=10)
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
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Watchlist service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": "Unable to retrieve watchlist entry at this time"}

# ====== Other Tools ======
@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str, result_filter: str = "web", search_lang: str = "en_US", 
               country: str = "US", ui_lang: str = "en", count: int = 10, 
               offset: int = 0, safesearch: str = "moderate"):
    """Perform a web search using the Brave Search API through our web search endpoint."""
    try:
        print(f"[LOG] web_search called with query='{query}', filter='{result_filter}', count={count}")
        
        # Validate inputs
        if not query or not query.strip():
            print(f"[LOG] Validation failed: query is empty")
            return {"ok": False, "error": "Search query cannot be empty"}
        
        if len(query.strip()) > 500:
            print(f"[LOG] Validation failed: query too long ({len(query.strip())} chars)")
            return {"ok": False, "error": "Search query cannot exceed 500 characters"}
        
        query = query.strip()
        
        # Validate count
        if count < 1 or count > 50:
            print(f"[LOG] Validation failed: count out of range ({count})")
            return {"ok": False, "error": "Count must be between 1 and 50"}
        
        # Validate offset
        if offset < 0:
            print(f"[LOG] Validation failed: offset negative ({offset})")
            return {"ok": False, "error": "Offset cannot be negative"}
        
        print(f"[LOG] Making API request to web search endpoint")
        
        # Prepare the request payload
        payload = {
            "query": query,
            "result_filter": result_filter,
            "search_lang": search_lang,
            "country": country,
            "ui_lang": ui_lang,
            "count": count,
            "offset": offset,
            "safesearch": safesearch
        }
        
        print(f"[LOG] API payload: {payload}")
        
        # Make HTTP request to the web search API
        response = requests.post(
            WEB_SEARCH_API_URL, 
            json=payload, 
            headers={"Content-Type": "application/json"}, 
            timeout=30
        )
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            
            # Extract relevant information from the response
            search_results = {
                "query": result.get("query", {}).get("original", query),
                "total_results": 0,
                "results": [],
                "result_type": result_filter
            }
            
            # Handle different result types
            if result_filter == "news" and "news" in result:
                news_data = result["news"]
                search_results["total_results"] = news_data.get("total", 0)
                search_results["results"] = news_data.get("results", [])
            elif result_filter == "videos" and "videos" in result:
                videos_data = result["videos"]
                search_results["total_results"] = videos_data.get("total", 0)
                search_results["results"] = videos_data.get("results", [])
            elif result_filter == "locations" and "locations" in result:
                locations_data = result["locations"]
                search_results["total_results"] = locations_data.get("total", 0)
                search_results["results"] = locations_data.get("results", [])
            elif result_filter == "faq" and "faq" in result:
                faq_data = result["faq"]
                search_results["total_results"] = faq_data.get("total", 0)
                search_results["results"] = faq_data.get("results", [])
            elif result_filter == "discussions" and "discussions" in result:
                discussions_data = result["discussions"]
                search_results["total_results"] = discussions_data.get("total", 0)
                search_results["results"] = discussions_data.get("results", [])
            elif result_filter == "infobox" and "infobox" in result:
                infobox_data = result["infobox"]
                search_results["infobox"] = infobox_data
            elif result_filter == "mixed":
                # For mixed results, combine all available result types
                all_results = []
                total_count = 0
                for result_type in ["web", "news", "videos", "locations"]:
                    if result_type in result:
                        type_data = result[result_type]
                        type_results = type_data.get("results", [])
                        all_results.extend(type_results[:count//4])  # Distribute evenly
                        total_count += type_data.get("total", 0)
                search_results["total_results"] = total_count
                search_results["results"] = all_results[:count]
            else:
                # Default to web results
                web_data = result.get("web", {})
                search_results["total_results"] = web_data.get("total", 0)
                search_results["results"] = web_data.get("results", [])
            
            return {
                "ok": True,
                "search_results": search_results,
                "message": f"Successfully performed {result_filter} search for '{query}'"
            }
            
        elif response.status_code == 400:
            result = response.json()
            print(f"[LOG] API response error 400: {result}")
            return {"ok": False, "error": result.get("detail", "Invalid search request")}
        elif response.status_code == 401:
            print(f"[LOG] API response error 401: Unauthorized")
            return {"ok": False, "error": "Web search service authentication failed"}
        elif response.status_code == 429:
            print(f"[LOG] API response error 429: Rate limit exceeded")
            return {"ok": False, "error": "Web search rate limit exceeded. Please try again later."}
        elif response.status_code == 500:
            result = response.json()
            print(f"[LOG] API response error 500: {result}")
            error_msg = result.get("detail", "Web search service error")
            if "API key not configured" in error_msg:
                return {"ok": False, "error": "Web search service not properly configured"}
            return {"ok": False, "error": error_msg}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            return {"ok": False, "error": f"Web search service error (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to web search API")
        return {"ok": False, "error": "Unable to connect to web search service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to web search API")
        return {"ok": False, "error": "Web search request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error during web search: {str(e)}"}

# ====== Stress Test Tool ======
@tool("stress_test", args_schema=StressTestInput)
def stress_test(target_url: str, num_requests: int = 10, timeout_seconds: int = 5):
    """Perform a simple stress test by sending multiple concurrent HTTP requests to a target URL."""
    try:
        print(f"[LOG] stress_test called with target_url={target_url}, num_requests={num_requests}, timeout_seconds={timeout_seconds}")
        
        # Validate inputs
        if not target_url or not target_url.strip():
            return {"ok": False, "error": "Target URL cannot be empty"}
        
        if not target_url.startswith(('http://', 'https://')):
            return {"ok": False, "error": "Target URL must start with http:// or https://"}
        
        target_url = target_url.strip()
        
        print(f"[LOG] Starting stress test with {num_requests} requests to {target_url}")
        
        import concurrent.futures
        import time
        
        results = {
            "successful": 0,
            "failed": 0,
            "total_time": 0,
            "avg_response_time": 0,
            "status_codes": {},
            "errors": []
        }
        
        start_time = time.time()
        
        def make_request():
            try:
                response = requests.get(target_url, timeout=timeout_seconds)
                return {
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "success": True
                }
            except requests.exceptions.Timeout:
                return {
                    "status_code": None,
                    "response_time": timeout_seconds,
                    "success": False,
                    "error": "Timeout"
                }
            except requests.exceptions.ConnectionError:
                return {
                    "status_code": None,
                    "response_time": 0,
                    "success": False,
                    "error": "Connection Error"
                }
            except Exception as e:
                return {
                    "status_code": None,
                    "response_time": 0,
                    "success": False,
                    "error": str(e)
                }
        
        # Use ThreadPoolExecutor for concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_requests, 20)) as executor:
            # Submit all requests
            future_to_request = {executor.submit(make_request): i for i in range(num_requests)}
            
            # Collect results as they complete
            response_times = []
            for future in concurrent.futures.as_completed(future_to_request):
                result = future.result()
                
                if result["success"]:
                    results["successful"] += 1
                    response_times.append(result["response_time"])
                    
                    # Track status codes
                    status_code = result["status_code"]
                    results["status_codes"][status_code] = results["status_codes"].get(status_code, 0) + 1
                else:
                    results["failed"] += 1
                    results["errors"].append(result["error"])
        
        total_time = time.time() - start_time
        results["total_time"] = total_time
        
        if response_times:
            results["avg_response_time"] = sum(response_times) / len(response_times)
        
        # Calculate success rate
        success_rate = (results["successful"] / num_requests) * 100 if num_requests > 0 else 0
        
        print(f"[LOG] Stress test completed: {results['successful']}/{num_requests} successful ({success_rate:.1f}%)")
        
        return {
            "ok": True,
            "message": f"Stress test completed for {target_url}",
            "results": {
                "target_url": target_url,
                "total_requests": num_requests,
                "successful_requests": results["successful"],
                "failed_requests": results["failed"],
                "success_rate_percent": round(success_rate, 1),
                "total_test_time_seconds": round(total_time, 2),
                "average_response_time_seconds": round(results["avg_response_time"], 3),
                "status_code_distribution": results["status_codes"],
                "common_errors": list(set(results["errors"])) if results["errors"] else []
            }
        }
        
    except Exception as e:
        print(f"[LOG] Unexpected error during stress test: {str(e)}")
        return {"ok": False, "error": f"Unexpected error during stress test: {str(e)}"}

# ====== User Preferences Tools ======
@tool("get_user_preferences", args_schema=GetUserPreferencesInput)
def get_user_preferences(user_id: str):
    """Get user preferences by user ID from the external user preferences API."""
    try:
        print(f"[LOG] get_user_preferences called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        print(f"[LOG] Making API request to get user preferences for user {user_id}")
        
        # Make HTTP request to the user preferences API
        api_url = f"{USER_PREFERENCES_API_URL}{user_id}"
        
        response = requests.get(api_url, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "preferences": result,
                "user_id": user_id
            }
        elif response.status_code == 404:
            return {"ok": False, "error": "User preferences not found"}
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                return {"ok": False, "error": f"User preferences API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve user preferences (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to user preferences service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "User preferences service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving user preferences: {str(e)}"}

@tool("create_user_preferences", args_schema=UserPreferencesInput)
def create_user_preferences(user_id: str, experience_level: Optional[str] = None, 
                           investment_style: Optional[str] = None, risk_tolerance: Optional[str] = None,
                           communication_style: Optional[str] = None, preferred_sectors: Optional[List[str]] = None,
                           investment_goals: Optional[List[str]] = None, preferred_timeframe: Optional[str] = None,
                           preferred_asset_classes: Optional[List[str]] = None, language: Optional[str] = None,
                           currency: Optional[str] = None, timezone: Optional[str] = None):
    """Create new user preferences by calling the external user preferences API."""
    try:
        print(f"[LOG] create_user_preferences called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        # Build payload with only provided values
        payload = {"user_id": user_id}
        if experience_level:
            payload["experience_level"] = experience_level
        if investment_style:
            payload["investment_style"] = investment_style
        if risk_tolerance:
            payload["risk_tolerance"] = risk_tolerance
        if communication_style:
            payload["communication_style"] = communication_style
        if preferred_sectors:
            payload["preferred_sectors"] = preferred_sectors
        if investment_goals:
            payload["investment_goals"] = investment_goals
        if preferred_timeframe:
            payload["preferred_timeframe"] = preferred_timeframe
        if preferred_asset_classes:
            payload["preferred_asset_classes"] = preferred_asset_classes
        if language:
            payload["language"] = language
        if currency:
            payload["currency"] = currency
        if timezone:
            payload["timezone"] = timezone
        
        print(f"[LOG] Making API request to create user preferences for user {user_id}")
        print(f"[LOG] API payload: {payload}")
        
        # Make HTTP request to the user preferences API
        response = requests.post(USER_PREFERENCES_API_URL, json=payload, 
                               headers={"Content-Type": "application/json"}, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "message": "Successfully created user preferences",
                "preferences": result,
                "user_id": user_id
            }
        elif response.status_code == 400:
            result = response.json()
            return {"ok": False, "error": result.get("detail", "Unable to create user preferences")}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            return {"ok": False, "error": "Unable to create user preferences at this time"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to user preferences service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "User preferences service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error creating user preferences: {str(e)}"}

@tool("update_user_preferences", args_schema=UserPreferencesInput)
def update_user_preferences(user_id: str, experience_level: Optional[str] = None, 
                           investment_style: Optional[str] = None, risk_tolerance: Optional[str] = None,
                           communication_style: Optional[str] = None, preferred_sectors: Optional[List[str]] = None,
                           investment_goals: Optional[List[str]] = None, preferred_timeframe: Optional[str] = None,
                           preferred_asset_classes: Optional[List[str]] = None, language: Optional[str] = None,
                           currency: Optional[str] = None, timezone: Optional[str] = None):
    """Update user preferences by calling the external user preferences API."""
    try:
        print(f"[LOG] update_user_preferences called with user_id={user_id}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        # Build payload with only provided values
        payload = {}
        if experience_level:
            payload["experience_level"] = experience_level
        if investment_style:
            payload["investment_style"] = investment_style
        if risk_tolerance:
            payload["risk_tolerance"] = risk_tolerance
        if communication_style:
            payload["communication_style"] = communication_style
        if preferred_sectors:
            payload["preferred_sectors"] = preferred_sectors
        if investment_goals:
            payload["investment_goals"] = investment_goals
        if preferred_timeframe:
            payload["preferred_timeframe"] = preferred_timeframe
        if preferred_asset_classes:
            payload["preferred_asset_classes"] = preferred_asset_classes
        if language:
            payload["language"] = language
        if currency:
            payload["currency"] = currency
        if timezone:
            payload["timezone"] = timezone
        
        if not payload:
            return {"ok": False, "error": "No fields provided for update"}
        
        print(f"[LOG] Making API request to update user preferences for user {user_id}")
        print(f"[LOG] API payload: {payload}")
        
        # Make HTTP request to the user preferences API
        api_url = f"{USER_PREFERENCES_API_URL}{user_id}"
        response = requests.put(api_url, json=payload, 
                              headers={"Content-Type": "application/json"}, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "message": "Successfully updated user preferences",
                "preferences": result,
                "user_id": user_id
            }
        elif response.status_code == 404:
            return {"ok": False, "error": "User preferences not found"}
        elif response.status_code == 400:
            result = response.json()
            return {"ok": False, "error": result.get("detail", "Unable to update user preferences")}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            return {"ok": False, "error": "Unable to update user preferences at this time"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to user preferences service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "User preferences service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error updating user preferences: {str(e)}"}

@tool("record_user_interaction", args_schema=UserInteractionInput)
def record_user_interaction(user_id: str, interaction_type: str, content: Optional[Dict[str, Any]] = None,
                           satisfaction_score: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
    """Record a user interaction by calling the external user interactions API."""
    try:
        print(f"[LOG] record_user_interaction called with user_id={user_id}, type={interaction_type}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        if not interaction_type or not interaction_type.strip():
            return {"ok": False, "error": "Interaction type cannot be empty"}
        
        user_id = user_id.strip()
        interaction_type = interaction_type.strip()
        
        # Build payload
        payload = {
            "user_id": user_id,
            "interaction_type": interaction_type
        }
        if content:
            payload["content"] = content
        if satisfaction_score:
            payload["satisfaction_score"] = satisfaction_score
        if metadata:
            payload["metadata"] = metadata
        
        print(f"[LOG] Making API request to record user interaction for user {user_id}")
        print(f"[LOG] API payload: {payload}")
        
        # Make HTTP request to the user interactions API
        response = requests.post(USER_INTERACTIONS_API_URL, json=payload, 
                               headers={"Content-Type": "application/json"}, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "message": "Successfully recorded user interaction",
                "interaction": result,
                "user_id": user_id
            }
        elif response.status_code == 400:
            result = response.json()
            return {"ok": False, "error": result.get("detail", "Unable to record user interaction")}
        else:
            print(f"[LOG] API response unexpected status: {response.status_code}")
            return {"ok": False, "error": "Unable to record user interaction at this time"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to user interactions service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "User interactions service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error recording user interaction: {str(e)}"}

@tool("get_user_interactions", args_schema=GetUserInteractionsInput)
def get_user_interactions(user_id: str, page: int = 1, size: int = 10, interaction_type: Optional[str] = None):
    """Get user interactions for a specific user from the external user interactions API."""
    try:
        print(f"[LOG] get_user_interactions called with user_id={user_id}, page={page}, size={size}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        # Build query parameters
        params = {"user_id": user_id, "page": page, "size": size}
        if interaction_type:
            params["interaction_type"] = interaction_type
        
        print(f"[LOG] Making API request to get user interactions for user {user_id}")
        
        # Make HTTP request to the user interactions API
        api_url = f"{USER_INTERACTIONS_API_URL}user/{user_id}"
        response = requests.get(api_url, params=params, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "interactions": result.get("interactions", []),
                "total": result.get("total", 0),
                "page": result.get("page", page),
                "size": result.get("size", size),
                "pages": result.get("pages", 0),
                "user_id": user_id
            }
        elif response.status_code == 404:
            return {"ok": False, "error": "User interactions not found"}
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                return {"ok": False, "error": f"User interactions API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve user interactions (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to user interactions service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "User interactions service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving user interactions: {str(e)}"}

@tool("get_preference_history", args_schema=GetPreferenceHistoryInput)
def get_preference_history(user_id: str, page: int = 1, size: int = 10, field_name: Optional[str] = None):
    """Get preference history for a specific user from the external preference history API."""
    try:
        print(f"[LOG] get_preference_history called with user_id={user_id}, page={page}, size={size}")
        
        if not user_id or not user_id.strip():
            return {"ok": False, "error": "User ID cannot be empty"}
        
        user_id = user_id.strip()
        
        # Build query parameters
        params = {"user_id": user_id, "page": page, "size": size}
        if field_name:
            params["field_name"] = field_name
        
        print(f"[LOG] Making API request to get preference history for user {user_id}")
        
        # Make HTTP request to the preference history API
        api_url = f"{PREFERENCE_HISTORY_API_URL}user/{user_id}"
        response = requests.get(api_url, params=params, timeout=10)
        print(f"[LOG] API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] API response success: {result}")
            return {
                "ok": True,
                "history": result.get("history", []),
                "total": result.get("total", 0),
                "page": result.get("page", page),
                "size": result.get("size", size),
                "pages": result.get("pages", 0),
                "user_id": user_id
            }
        elif response.status_code == 404:
            return {"ok": False, "error": "Preference history not found"}
        else:
            print(f"[LOG] API response failed with status {response.status_code}")
            try:
                error_detail = response.json()
                return {"ok": False, "error": f"Preference history API error: {error_detail.get('detail', 'Unknown error')}"}
            except:
                return {"ok": False, "error": f"Unable to retrieve preference history (HTTP {response.status_code})"}
        
    except requests.exceptions.ConnectionError:
        print(f"[LOG] Connection error to API")
        return {"ok": False, "error": "Unable to connect to preference history service. Please check if the service is running."}
    except requests.exceptions.Timeout:
        print(f"[LOG] Timeout error to API")
        return {"ok": False, "error": "Preference history service request timed out. Please try again."}
    except Exception as e:
        print(f"[LOG] Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error retrieving preference history: {str(e)}"}

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
    stress_test,
    get_user_preferences,
    create_user_preferences,
    update_user_preferences,
    record_user_interaction,
    get_user_interactions,
    get_preference_history,
]
