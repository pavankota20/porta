# Porta Finance Assistant API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [AI Agent Tools](#ai-agent-tools)
7. [Error Handling](#error-handling)
8. [Usage Examples](#usage-examples)
9. [Rate Limiting](#rate-limiting)
10. [WebSocket Support](#websocket-support)

## Overview

Porta Finance Assistant is a comprehensive financial portfolio and watchlist management system with AI assistance. The API provides endpoints for managing portfolios, watchlists, user preferences, and AI-powered financial assistance.

## Base URL

```
http://localhost:8001
```

## Authentication

Currently, the API uses user ID-based authentication. Pass your `user_id` in request headers or body parameters.

**Default User ID**: `f00dc8bd-eabc-4143-b1f0-fbcb9715a02e`

## API Endpoints

### 1. Health & Status

#### GET `/`
**Description**: Root endpoint with API information
**Response**: Basic API status and version information

**Example Response**:
```json
{
  "message": "Porta Finance Assistant API",
  "status": "running",
  "version": "1.0.0"
}
```

#### GET `/health`
**Description**: Detailed health check endpoint
**Response**: Comprehensive system health information

**Example Response**:
```json
{
  "status": "healthy",
  "agent_ready": true,
  "tools_available": 15,
  "tool_names": ["add_to_portfolio", "remove_from_portfolio", "list_portfolio", ...],
  "async_processing": {
    "queue_size": 0,
    "active_requests": 0,
    "max_concurrent": 5
  }
}
```

### 2. AI Chat Endpoints

#### POST `/chat`
**Description**: Send a message to the AI finance assistant
**Request Body**: `ChatRequest`

**Request Model**:
```json
{
  "message": "Add 100 shares of AAPL at $150 to my portfolio",
  "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e",
  "session_id": "optional-session-id",
  "chat_history": []
}
```

**Response Model**: `ChatResponse`
```json
{
  "response": "Successfully added 100 shares of AAPL at $150 to your portfolio.",
  "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e",
  "session_id": "session-uuid",
  "status": "success"
}
```

#### POST `/chat/async`
**Description**: Send a message to the AI assistant asynchronously
**Request Body**: `AsyncChatRequest`

**Response Model**: `AsyncChatResponse`
```json
{
  "request_id": "uuid-string",
  "status": "processing",
  "message": "Request submitted successfully"
}
```

#### GET `/request-status/{request_id}`
**Description**: Check the status of an async request
**Response Model**: `RequestStatusResponse`

#### GET `/active-requests`
**Description**: List all active async requests
**Response**: List of active request IDs and statuses

#### GET `/user-sessions/{user_id}`
**Description**: Get all chat sessions for a user
**Response**: List of session information

#### GET `/session-messages/{session_id}`
**Description**: Get messages from a specific chat session
**Response**: List of messages with metadata

#### DELETE `/close-session/{session_id}`
**Description**: Close a chat session
**Response**: Success confirmation

### 3. Web Search Endpoint

#### POST `/api/v1/web-search/`
**Description**: Perform web searches using Brave Search API
**Request Body**: `WebSearchInput`

**Request Model**:
```json
{
  "query": "Apple stock price today",
  "result_filter": "web",
  "search_lang": "en_US",
  "country": "US",
  "ui_lang": "en",
  "count": 10,
  "offset": 0,
  "safesearch": "moderate"
}
```

**Response**: Search results from Brave Search API

## Data Models

### Core Models

#### ChatRequest
```python
class ChatRequest(BaseModel):
    message: str                    # User's message/prompt
    user_id: str                   # User identifier
    session_id: Optional[str]      # Chat session ID
    chat_history: List[Dict]       # Previous chat history
```

#### ChatResponse
```python
class ChatResponse(BaseModel):
    response: str                   # Agent's response
    user_id: str                   # User identifier
    session_id: str                # Chat session ID
    status: str                    # Response status
```

#### AsyncChatRequest
```python
class AsyncChatRequest(BaseModel):
    message: str                    # User's message/prompt
    user_id: str                   # User identifier
    chat_history: List[Dict]       # Previous chat history
```

#### AsyncChatResponse
```python
class AsyncChatResponse(BaseModel):
    request_id: str                 # Unique request identifier
    status: str                     # Request status
    message: str                    # Status message
```

#### RequestStatusResponse
```python
class RequestStatusResponse(BaseModel):
    request_id: str                 # Unique request identifier
    status: str                     # Request status
    response: Optional[str]         # Agent's response
    user_id: str                    # User identifier
    error: Optional[str]            # Error message if any
    created_at: str                 # Request creation timestamp
    completed_at: Optional[str]     # Request completion timestamp
```

### Web Search Models

#### WebSearchInput
```python
class WebSearchInput(BaseModel):
    query: str                      # Search query string (1-500 characters)
    result_filter: Optional[str]    # Filter results by type
    search_lang: Optional[str]      # Search language (e.g., en_US)
    country: Optional[str]          # Country code (e.g., US)
    ui_lang: Optional[str]          # UI language (e.g., en)
    count: Optional[int]            # Number of results (1-50)
    offset: Optional[int]           # Offset for pagination
    safesearch: Optional[str]       # Safe search setting
```

### Tool Input Models

#### Portfolio Tools
```python
class AddPortfolioInput(BaseModel):
    user_id: str                    # User identifier
    ticker: Ticker                  # Stock ticker symbol
    quantity: str                   # Number of shares
    buy_price: str                  # Purchase price per share
    note: Optional[str]             # Optional note

class RemovePortfolioInput(BaseModel):
    user_id: str                    # User identifier
    ticker: Ticker                  # Stock ticker symbol

class ListPortfolioInput(BaseModel):
    user_id: str                    # User identifier

class GetPortfolioSummaryInput(BaseModel):
    user_id: str                    # User identifier
    include_pnl: bool               # Include PnL calculations
```

#### Watchlist Tools
```python
class AddWatchlistInput(BaseModel):
    user_id: str                    # User identifier
    ticker: Ticker                  # Stock ticker symbol
    note: Optional[str]             # Optional note

class RemoveWatchlistInput(BaseModel):
    user_id: str                    # User identifier
    ticker: Ticker                  # Stock ticker symbol

class ListWatchlistInput(BaseModel):
    user_id: str                    # User identifier

class GetWatchlistEntryInput(BaseModel):
    user_id: str                    # User identifier
    ticker: Ticker                  # Stock ticker symbol
```

#### User Preferences Tools
```python
class UserPreferencesInput(BaseModel):
    user_id: str                    # User identifier
    experience_level: str           # Investment experience level
    investment_style: str           # Investment style
    risk_tolerance: str             # Risk tolerance
    communication_style: str        # Preferred communication style
    preferred_sectors: List[str]    # Preferred investment sectors
    preferred_asset_classes: List[str] # Preferred asset classes
    investment_timeframe: str       # Investment timeframe
    financial_goals: List[str]      # Financial goals
    notes: Optional[str]            # Additional notes

class GetUserPreferencesInput(BaseModel):
    user_id: str                    # User identifier

class ListUserPreferencesInput(BaseModel):
    user_id: str                    # User identifier

class UserInteractionInput(BaseModel):
    user_id: str                    # User identifier
    interaction_type: str           # Type of interaction
    content: str                    # Interaction content
    satisfaction_rating: Optional[int] # Satisfaction rating (1-5)
    feedback: Optional[str]         # User feedback
```

## AI Agent Tools

The AI agent has access to the following tools for managing portfolios and watchlists:

### Portfolio Management Tools

#### `add_to_portfolio`
**Description**: Add or update a holding in the user's portfolio
**Parameters**:
- `user_id`: User identifier
- `ticker`: Stock ticker symbol (e.g., "AAPL")
- `quantity`: Number of shares (e.g., "100.0000")
- `buy_price`: Purchase price per share (e.g., "150.5000")
- `note`: Optional note about the holding

**Example Usage**:
```
"Add 100 shares of Apple at $150 to my portfolio"
```

#### `remove_from_portfolio`
**Description**: Remove a holding from the user's portfolio
**Parameters**:
- `user_id`: User identifier
- `ticker`: Stock ticker symbol to remove

**Example Usage**:
```
"Remove Microsoft from my portfolio"
```

#### `list_portfolio`
**Description**: List all holdings in the user's portfolio
**Parameters**:
- `user_id`: User identifier

**Example Usage**:
```
"Show my portfolio"
```

#### `get_portfolio_summary`
**Description**: Get a summary of the user's portfolio with PnL calculations
**Parameters**:
- `user_id`: User identifier
- `include_pnl`: Whether to include PnL calculations (default: true)

**Example Usage**:
```
"Give me a portfolio summary with PnL"
```

### Watchlist Management Tools

#### `add_to_watchlist`
**Description**: Add a stock to the user's watchlist
**Parameters**:
- `user_id`: User identifier
- `ticker`: Stock ticker symbol
- `note`: Optional note about the stock

**Example Usage**:
```
"Add Tesla to my watchlist"
```

#### `remove_from_watchlist`
**Description**: Remove a stock from the user's watchlist
**Parameters**:
- `user_id`: User identifier
- `ticker`: Stock ticker symbol to remove

**Example Usage**:
```
"Remove GameStop from my watchlist"
```

#### `list_watchlist`
**Description**: List all stocks in the user's watchlist
**Parameters**:
- `user_id`: User identifier

**Example Usage**:
```
"Show my watchlist"
```

#### `get_watchlist_entry`
**Description**: Get details about a specific watchlist entry
**Parameters**:
- `user_id`: User identifier
- `ticker`: Stock ticker symbol

**Example Usage**:
```
"Show me details about Apple in my watchlist"
```

### User Preferences Tools

#### `get_user_preferences`
**Description**: Retrieve user preferences and investment profile
**Parameters**:
- `user_id`: User identifier

#### `create_user_preferences`
**Description**: Create a new user preferences profile
**Parameters**: `UserPreferencesInput` model

#### `update_user_preferences`
**Description**: Update existing user preferences
**Parameters**: `UserPreferencesInput` model

#### `record_user_interaction`
**Description**: Record user interactions and satisfaction
**Parameters**: `UserInteractionInput` model

#### `get_user_interactions`
**Description**: Retrieve user interaction history
**Parameters**: `GetUserInteractionsInput` model

#### `get_preference_history`
**Description**: View how user preferences have changed over time
**Parameters**: `GetPreferenceHistoryInput` model

### Utility Tools

#### `web_search`
**Description**: Perform web searches for financial information
**Parameters**: `WebSearchInput` model

**Example Usage**:
```
"Search for latest Apple earnings report"
```

#### `stress_test_api`
**Description**: Test API endpoints for performance and reliability
**Parameters**:
- `target_url`: URL to test
- `num_requests`: Number of concurrent requests (1-100)
- `timeout_seconds`: Timeout for each request (1-30)

## Error Handling

### HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "detail": "Error message description",
  "status_code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common Error Scenarios

1. **Missing Required Fields**: When required parameters are not provided
2. **Invalid Ticker Format**: When stock ticker doesn't match expected pattern
3. **API Service Unavailable**: When external portfolio/watchlist services are down
4. **Invalid User ID**: When user identifier is not found
5. **Session Expired**: When chat session has expired

## Usage Examples

### 1. Adding a Stock to Portfolio

**Request**:
```bash
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add 50 shares of Microsoft at $300 to my portfolio",
    "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"
  }'
```

**Response**:
```json
{
  "response": "Successfully added 50 shares of Microsoft at $300 to your portfolio.",
  "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e",
  "session_id": "session-uuid-here",
  "status": "success"
}
```

### 2. Checking Portfolio Summary

**Request**:
```bash
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show my portfolio summary with PnL",
    "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"
  }'
```

### 3. Adding to Watchlist

**Request**:
```bash
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add NVIDIA to my watchlist",
    "user_id": "f00dc8bd-eabc-4143-b1f0-fbcb9715a02e"
  }'
```

### 4. Web Search

**Request**:
```bash
curl -X POST "http://localhost:8001/api/v1/web-search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Federal Reserve interest rate decision 2024",
    "count": 5,
    "result_filter": "news"
  }'
```

## Rate Limiting

- **Chat Endpoints**: 100 requests per minute per user
- **Web Search**: 50 requests per minute per user
- **Portfolio Operations**: 200 requests per minute per user
- **User Preferences**: 100 requests per minute per user

## WebSocket Support

Currently, the API supports long-polling for async requests. WebSocket support for real-time chat is planned for future releases.

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-7-sonnet-20250219

# Optional
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
BRAVE_SEARCH_BASE_URL=https://api.search.brave.com/res/v1/web/search

# Database
POSTGRES_SERVER=your_postgres_server
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=your_postgres_db
POSTGRES_PORT=5432
```

### Server Configuration

- **Host**: 127.0.0.1 (configurable)
- **Port**: 8001 (configurable)
- **Max Concurrent Requests**: 5
- **Max Stored Requests**: 100
- **Request Timeout**: 30 seconds

## Development

### Running the API

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your_key_here"

# Run the server
python -m uvicorn agent:app --host 127.0.0.1 --port 8001 --reload
```

### Testing

```bash
# Run tests
pytest

# Check API health
curl http://localhost:8001/health
```

## Support

For API support and questions:
- Check the health endpoint: `GET /health`
- Review error logs in the console output
- Ensure all required services are running
- Verify API keys and configuration

## Changelog

### Version 1.0.0
- Initial API release
- Portfolio and watchlist management
- AI-powered financial assistance
- User preferences and interactions
- Web search integration
- Async request processing
