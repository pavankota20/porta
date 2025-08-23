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

class GetNewsInput(BaseModel):
    user_id: str = Field(default="f00dc8bd-eabc-4143-b1f0-fbcb9715a02e")
    ticker: Ticker
    lookback_days: int = Field(default=3, ge=1, le=30)

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query string (1-500 characters)")
    result_filter: Optional[str] = Field(default="web", description="Filter results by type (web, news, videos, locations, faq, discussions, infobox, mixed, summarizer, rich)")
    search_lang: Optional[str] = Field(default="en_US", description="Search language (e.g., en_US, fr_FR)")
    country: Optional[str] = Field(default="US", description="Country code (e.g., US, FR)")
    ui_lang: Optional[str] = Field(default="en", description="UI language (e.g., en, fr)")
    count: Optional[int] = Field(default=10, ge=1, le=50, description="Number of results (1-50)")
    offset: Optional[int] = Field(default=0, ge=0, description="Offset for pagination")
    safesearch: Optional[str] = Field(default="moderate", description="Safe search setting (strict, moderate, off)")

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
