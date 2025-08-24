#!/usr/bin/env python3
"""
Pydantic models for Porta Finance Assistant API
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, constr

# ====== Type Definitions ======
Ticker = constr(pattern=r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$")

# ====== Tool Input Models ======
class AddPortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    quantity: str = Field(..., description="Number of shares (e.g., '100.0000')")
    buy_price: str = Field(..., description="Purchase price per share (e.g., '150.5000')")
    note: Optional[str] = None

class RemovePortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker

class ListPortfolioInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")

class GetPortfolioSummaryInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    include_pnl: bool = Field(default=True, description="Include PnL calculations")

class AddWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    note: Optional[str] = None

class RemoveWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker

class ListWatchlistInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")

class GetWatchlistEntryInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query string (1-500 characters)")
    result_filter: Optional[str] = Field(default="web", description="Filter results by type (web, news, videos, locations, faq, discussions, infobox, mixed, summarizer, rich)")
    search_lang: Optional[str] = Field(default="en_US", description="Search language (e.g., en_US, fr_FR)")
    country: Optional[str] = Field(default="US", description="Country code (e.g., US, FR)")
    ui_lang: Optional[str] = Field(default="en", description="UI language (e.g., en, fr)")
    count: Optional[int] = Field(default=10, ge=1, le=50, description="Number of results (1-50)")
    offset: Optional[int] = Field(default=0, ge=0, description="Offset for pagination")
    safesearch: Optional[str] = Field(default="moderate", description="Safe search setting (strict, moderate, off)")

class StressTestInput(BaseModel):
    target_url: str = Field(..., description="URL to stress test (e.g., 'http://localhost:8000/health')")
    num_requests: int = Field(default=10, ge=1, le=100, description="Number of concurrent requests to send (1-100)")
    timeout_seconds: int = Field(default=5, ge=1, le=30, description="Timeout for each request in seconds (1-30)")

# ====== API Request/Response Models ======
class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message/prompt")
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e", description="User identifier")
    session_id: Optional[str] = Field(None, description="Chat session ID (optional, will create new if not provided)")
    chat_history: List[Dict[str, str]] = Field(default=[], description="Previous chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Chat session ID")
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

# ====== User Preferences Models ======
class UserPreferences(BaseModel):
    user_id: str
    experience_level: str = Field(..., description="User's investment experience level")
    investment_style: str = Field(..., description="User's investment style")
    risk_tolerance: str = Field(..., description="User's risk tolerance")
    communication_style: str = Field(..., description="User's preferred communication style")
    preferred_sectors: List[str] = Field(default=[], description="User's preferred investment sectors")
    investment_goals: List[str] = Field(default=[], description="User's investment goals")
    preferred_timeframe: str = Field(..., description="User's preferred investment timeframe")
    preferred_asset_classes: List[str] = Field(default=[], description="User's preferred asset classes")
    language: str = Field(default="en", description="User's preferred language")
    currency: str = Field(default="USD", description="User's preferred currency")
    timezone: Optional[str] = Field(None, description="User's timezone")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UserPreferencesInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    experience_level: Optional[str] = Field(None, description="Experience level: beginner, intermediate, advanced, expert")
    investment_style: Optional[str] = Field(None, description="Investment style: conservative, moderate, aggressive, day_trader, swing_trader, long_term")
    risk_tolerance: Optional[str] = Field(None, description="Risk tolerance: low, medium, high")
    communication_style: Optional[str] = Field(None, description="Communication style: simple, technical, detailed")
    preferred_sectors: Optional[List[str]] = Field(None, description="Preferred sectors like technology, healthcare, etc.")
    investment_goals: Optional[List[str]] = Field(None, description="Investment goals like growth, retirement, etc.")
    preferred_timeframe: Optional[str] = Field(None, description="Preferred timeframe: short_term, medium_term, long_term")
    preferred_asset_classes: Optional[List[str]] = Field(None, description="Preferred asset classes like stocks, etfs, etc.")
    language: Optional[str] = Field(None, description="Preferred language code")
    currency: Optional[str] = Field(None, description="Preferred currency code")
    timezone: Optional[str] = Field(None, description="User's timezone")

class UserInteractionInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    interaction_type: str = Field(..., description="Type of interaction: tool_used, feedback_given, preference_changed, search_performed, portfolio_viewed")
    content: Optional[Dict[str, Any]] = Field(None, description="Interaction content details")
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5, description="Satisfaction score from 1-5")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the interaction")

class GetUserPreferencesInput(BaseModel):
    user_id: str = Field(..., description="User identifier")

class ListUserPreferencesInput(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    experience_level: Optional[str] = Field(None, description="Filter by experience level")
    investment_style: Optional[str] = Field(None, description="Filter by investment style")
    risk_tolerance: Optional[str] = Field(None, description="Filter by risk tolerance")

class GetUserInteractionsInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    interaction_type: Optional[str] = Field(None, description="Filter by interaction type")

class GetPreferenceHistoryInput(BaseModel):
    user_id: str = Field(..., description="User identifier")
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")
    field_name: Optional[str] = Field(None, description="Filter by field name")
