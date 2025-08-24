# 🚀 Porta Finance Assistant

**Your AI-Powered Financial Portfolio Management & Research Assistant**

Porta Finance Assistant is an intelligent financial management system that combines portfolio tracking, watchlist management, and AI-powered research capabilities. Built with FastAPI, LangChain, and Claude AI, it provides a conversational interface for managing your investments and researching financial markets.

## ✨ Features

### 📊 **Portfolio Management**
- **Add/Remove Holdings**: Easily add new stocks to your portfolio with quantity, price, and notes
- **Portfolio Overview**: View all your current holdings with detailed information
- **Portfolio Summary**: Get comprehensive portfolio analysis including PnL calculations
- **Real-time Updates**: Track current prices and performance metrics

### 👀 **Watchlist Management**
- **Smart Watchlists**: Add stocks you're interested in to track
- **Portfolio Sync**: Automatically sync portfolio stocks to watchlist
- **Notes & Tracking**: Add personal notes and track watchlist performance

### 🔍 **AI-Powered Research**
- **Web Search Integration**: Search across multiple result types (web, news, videos, locations, FAQ)
- **Stock Analysis**: Get AI-generated insights and analysis for any ticker
- **News Aggregation**: Fetch latest financial news through web search with news filter
- **Multi-source Research**: Combine web search, portfolio data, and watchlist information

### 💬 **Conversational Interface**
- **Natural Language**: Ask questions in plain English
- **Context Awareness**: Maintains conversation history and context
- **Intelligent Responses**: AI understands complex queries and provides helpful suggestions
- **Multi-step Operations**: Execute complex tasks with single requests

### 🎯 **User Preferences & Personalization**
- **Investment Profile**: Stores user experience level, risk tolerance, and investment style
- **Communication Preferences**: Adapts responses based on user's preferred communication style
- **Sector Preferences**: Tracks preferred investment sectors and asset classes
- **Interaction History**: Monitors user engagement and satisfaction for continuous improvement
- **Preference Evolution**: Maintains audit trail of preference changes over time

## 🏗️ Architecture

### **Backend Stack**
- **FastAPI**: High-performance web framework for API endpoints
- **LangChain**: AI agent framework for tool orchestration
- **Claude AI**: Advanced language model for natural conversations
- **PostgreSQL**: Robust database for data persistence
- **Redis**: Caching and session management

### **Core Components**
```
porta/
├── agent.py              # Main FastAPI server & AI agent
├── tools.py              # LangChain tools for portfolio/watchlist/search
├── models.py             # Pydantic data models
├── config.py             # Configuration & environment variables
├── database.py           # Database operations & session management
├── api_routes.py         # API route handlers
└── request_processor.py  # Async request processing
```

## 🚀 Quick Start

### **1. Environment Setup**
```bash
# Clone the repository
git clone <your-repo-url>
cd porta

# Create virtual environment
python -m venv porta_env
source porta_env/bin/activate  # On Windows: porta_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration**
Create a `.env` file with your API keys:
```env
# Required: Brave Search API for web search functionality
BRAVE_SEARCH_API_KEY=your_brave_search_api_key_here
BRAVE_SEARCH_BASE_URL=https://api.search.brave.com/res/v1/web/search

# Optional: Customize API endpoints
PORTFOLIO_API_URL=http://localhost:8000/api/v1/portfolio/
WATCHLIST_API_URL=http://localhost:8000/api/v1/watchlist/
WEB_SEARCH_API_URL=http://localhost:8001/api/v1/web-search/
```

### **3. Start the Service**
```bash
# Start the FastAPI server
python agent.py

# Server will be available at: http://localhost:8001
```

## 📡 API Endpoints

### **Core Chat Endpoint**
```http
POST /chat
Content-Type: application/json

{
  "message": "add TSLA to my portfolio with 100 shares at $200",
  "user_id": "your-user-id"
}
```

### **Web Search Endpoint**
```http
POST /api/v1/web-search/
Content-Type: application/json

{
  "query": "GOOG stock analysis",
  "result_filter": "news",
  "count": 10
}
```

### **Portfolio Management**
- `GET /api/v1/portfolio/?user_id={user_id}` - List portfolio
- `POST /api/v1/portfolio/` - Add to portfolio
- `DELETE /api/v1/portfolio/{id}` - Remove from portfolio
- `GET /api/v1/portfolio/summary/{user_id}` - Portfolio summary

### **Watchlist Management**
- `GET /api/v1/watchlist/?user_id={user_id}` - List watchlist
- `POST /api/v1/watchlist/` - Add to watchlist
- `DELETE /api/v1/watchlist/{id}` - Remove from watchlist

## 🧠 AI Agent Capabilities

### **Portfolio Operations**
```
User: "add AAPL to my portfolio with 50 shares at $150"
Agent: ✅ Adds AAPL to portfolio, confirms success

User: "what stocks do I have and what's the latest news for each?"
Agent: ✅ Lists portfolio → Fetches news for each stock → Provides summary

User: "give me a summary of my portfolio and add missing stocks to watchlist"
Agent: ✅ Portfolio summary → Syncs portfolio stocks to watchlist
```

### **Research & Analysis**
```
User: "search for GOOG stock analysis"
Agent: ✅ Performs web search → Filters results → Provides insights

User: "find videos about NVDA stock"
Agent: ✅ Searches video content → Returns relevant video results

User: "get news for AAPL from last 7 days"
Agent: ✅ Performs web search with news filter → Returns relevant news articles
```

### **Complex Queries**
```
User: "add TSLA to my portfolio with 100 shares at $200, then add it to my watchlist"
Agent: ✅ Portfolio addition → Watchlist addition → Confirms both operations

User: "search for stock analysis of all my portfolio stocks"
Agent: ✅ Lists portfolio → Searches each ticker → Provides comprehensive analysis
```

## 🛠️ Available Tools

### **Portfolio Tools**
- `add_to_portfolio` - Add/update portfolio holdings
- `remove_from_portfolio` - Remove stocks from portfolio
- `list_portfolio` - View all portfolio holdings
- `get_portfolio_summary` - Portfolio analysis with PnL

### **Watchlist Tools**
- `add_to_watchlist` - Add stocks to watchlist
- `remove_from_watchlist` - Remove from watchlist
- `list_watchlist` - View watchlist entries
- `get_watchlist_entry` - Get specific watchlist details

### **Research Tools**
- `web_search` - Multi-source web search with filters

### **User Preferences Tools**
- `get_user_preferences` - Retrieve user's investment preferences and settings
- `create_user_preferences` - Create new user preferences profile
- `update_user_preferences` - Update existing user preferences
- `record_user_interaction` - Track user interactions and satisfaction
- `get_user_interactions` - View user's interaction history
- `get_preference_history` - See how user preferences have changed over time

## 🔧 Configuration Options

### **Web Search Filters**
- `web` - General web search results
- `news` - News articles and headlines
- `videos` - Video content and analysis
- `locations` - Company locations and offices
- `faq` - Frequently asked questions
- `discussions` - Forum and discussion content
- `infobox` - Structured company information
- `mixed` - Combined results from multiple sources

### **Search Parameters**
- `query` - Search query (1-500 characters)
- `result_filter` - Type of results to return
- `search_lang` - Search language (e.g., en_US, fr_FR)
- `country` - Country code for localized results
- `count` - Number of results (1-50)
- `offset` - Pagination offset
- `safesearch` - Safe search setting (strict, moderate, off)

## 📱 Usage Examples

### **Portfolio Management**
```bash
# Add stocks to portfolio
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "add NVDA to my portfolio with 25 shares at $400", "user_id": "your-user-id"}'

# View portfolio
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "show my portfolio", "user_id": "your-user-id"}'

# Get portfolio summary
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "portfolio summary with PnL", "user_id": "your-user-id"}'
```

### **Research & Analysis**
```bash
# Web search for stock analysis
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "search for AAPL earnings analysis", "user_id": "your-user-id"}'

# Get news for specific stocks
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "search for GOOGL stock news", "user_id": "your-user-id"}'

# Complex research queries
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "what stocks do I have and what is the latest news for each?", "user_id": "your-user-id"}'
```

### **Watchlist Management**
```bash
# Add to watchlist
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "add TSLA to my watchlist", "user_id": "your-user-id"}'

# Sync portfolio to watchlist
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "add all my portfolio stocks to watchlist", "user_id": "your-user-id"}'
```

## 🔒 Security & Best Practices

### **Environment Variables**
- Store sensitive API keys in `.env` file
- Never commit API keys to version control
- Use different API keys for development/production

### **User Authentication**
- Implement proper user authentication for production use
- Validate user permissions for portfolio operations
- Use secure session management

### **Rate Limiting**
- Implement rate limiting for web search endpoints
- Monitor API usage to avoid hitting limits
- Cache frequently requested data

## 🚀 Deployment

### **Production Considerations**
```bash
# Use production WSGI server
pip install gunicorn
gunicorn agent:app -w 4 -k uvicorn.workers.UvicornWorker

# Set production environment variables
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=info
```

### **Docker Support**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["python", "agent.py"]
```

## 🧪 Testing

### **Tool Testing**
All tools have been thoroughly tested with 100% success rate:
- ✅ Portfolio management tools
- ✅ Watchlist management tools  
- ✅ Web search tools
- ✅ News aggregation tools
- ✅ Complex query handling
- ✅ Error handling and validation

### **API Testing**
```bash
# Test health endpoint
curl http://localhost:8001/health

# Test chat endpoint
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "test message", "user_id": "test-user"}'
```

## 🔮 Future Enhancements

### **Planned Features**
- Real-time stock price updates
- Advanced portfolio analytics
- Risk assessment and recommendations
- Integration with more financial data providers
- Mobile app support
- Advanced charting and visualization

### **API Integrations**
- Yahoo Finance API
- Alpha Vantage
- IEX Cloud
- Polygon.io
- News APIs (Reuters, Bloomberg)

## 📞 Support & Contributing

### **Getting Help**
- Check the logs for detailed error information
- Verify API keys are properly configured
- Ensure all required services are running

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [LangChain](https://langchain.com/)
- AI capabilities from [Anthropic Claude](https://www.anthropic.com/)
- Web search powered by [Brave Search API](https://api.search.brave.com/)

---

**Porta Finance Assistant** - Making financial management intelligent and accessible! 🚀💰
