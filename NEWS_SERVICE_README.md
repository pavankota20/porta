# News Aggregation Service for Porta Finance

## Overview
The News Aggregation Service is a standalone batch job that automatically fetches and processes financial news for all stocks in your portfolio AND watchlist. It runs every 30 seconds, ensuring you always have the latest news with AI-generated insights.

## What It Does

### 1. **Comprehensive Coverage**
- **Portfolio Items**: Fetches news for all stocks you currently own
- **Watchlist Items**: Fetches news for all stocks you're monitoring
- **Deduplication**: Prevents duplicate news using unique content hashing
- **Source Tracking**: Distinguishes between portfolio and watchlist news

### 2. **AI-Powered Processing**
- **LLM Analysis**: Each news article goes through Claude AI
- **3 Key Bullet Points**: Summarizes main insights for quick reading
- **Sentiment Analysis**: Identifies positive, negative, or neutral sentiment
- **Relevance Scoring**: Rates news importance (0.0 to 1.0) for investors

### 3. **Smart Caching & Rate Limiting**
- **Portfolio Cache**: Reduces API calls to your main service
- **Watchlist Cache**: Stores watchlist data for efficiency
- **Rate Limiting**: Respects API limits for news and LLM services
- **Error Handling**: Graceful fallbacks and comprehensive logging

## Database Schema

### News Table
```sql
news (
    news_id VARCHAR(255) PRIMARY KEY,      -- Unique hash of content
    ticker VARCHAR(20) NOT NULL,           -- Stock symbol
    title TEXT NOT NULL,                   -- News headline
    description TEXT,                      -- News summary
    url TEXT NOT NULL,                     -- Source URL
    source VARCHAR(100),                   -- News source (e.g., Reuters)
    published_at TIMESTAMP,                -- Publication date
    content TEXT,                          -- Full article content
    bullet_points JSONB,                   -- 3 AI-generated key points
    sentiment VARCHAR(20),                 -- positive/negative/neutral
    relevance_score DECIMAL(3,2),          -- 0.0 to 1.0 relevance
    ticker_source VARCHAR(20),             -- 'portfolio' or 'watchlist'
    created_at TIMESTAMP,                  -- When added to database
    updated_at TIMESTAMP                   -- Last update time
)
```

### Cache Tables
- `portfolio_cache`: Portfolio items data
- `watchlist_cache`: Watchlist tickers
- `news_processing_status`: Processing status for each ticker

## Configuration

### Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=your_claude_api_key
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
DATABASE_URL=your_postgres_connection_string

# Optional
PORTFOLIO_API_URL=http://localhost:8000/api/v1/portfolio/
DEFAULT_USER_ID=your_user_id
NEWS_UPDATE_INTERVAL_SECONDS=30
MAX_NEWS_PER_TICKER=15
```

### API Endpoints Used
- **Portfolio API**: `http://localhost:8000/api/v1/portfolio/{user_id}/holdings`
- **Watchlist API**: `http://localhost:8000/api/v1/watchlist/{user_id}/`
- **News API**: Brave Search API for financial news
- **LLM API**: Anthropic Claude for content processing

## How It Works

### 1. **Batch Processing Cycle** (Every 30 seconds)
```
Start → Fetch Portfolio → Fetch Watchlist → Combine Tickers → Process News → Store Results
```

### 2. **News Processing Pipeline**
```
News Article → LLM Analysis → Generate Bullet Points → Sentiment Analysis → Store in DB
```

### 3. **Deduplication Logic**
- Creates SHA256 hash from: `title + url + published_date`
- Prevents storing duplicate news articles
- Updates existing articles if content changes

## Running the Service

### Option 1: Direct Python
```bash
# Install dependencies
pip install -r requirements.txt

# Start service
python3 news_service.py
```

## Monitoring & Logs

### Log Files
- **Main Log**: `news_service.log`
- **Console Output**: Real-time logging to terminal
- **Log Level**: Configurable (INFO, DEBUG, ERROR)

### Database Queries
```sql
-- Get all news for a specific ticker
SELECT * FROM news WHERE ticker = 'AAPL' ORDER BY published_at DESC;

-- Get portfolio vs watchlist news
SELECT ticker, ticker_source, COUNT(*) as news_count 
FROM news 
GROUP BY ticker, ticker_source;

-- Get latest news with sentiment
SELECT ticker, title, sentiment, relevance_score, bullet_points 
FROM news 
WHERE published_at > NOW() - INTERVAL '24 hours'
ORDER BY relevance_score DESC;
```

## Performance & Scalability

### Current Limits
- **News per ticker**: 15 articles per run
- **Update frequency**: Every 30 seconds
- **LLM rate limit**: 0.5 second delay between calls
- **News API rate limit**: 1 second delay between tickers

### Optimization Features
- **Async processing**: Non-blocking operations
- **Connection pooling**: Efficient database connections
- **Smart caching**: Reduces redundant API calls
- **Batch processing**: Processes multiple tickers efficiently

## Error Handling

### Fallback Mechanisms
- **API failures**: Uses cached data when APIs are down
- **LLM errors**: Generates fallback bullet points
- **Database issues**: Retries with exponential backoff
- **Network problems**: Continues with available data

### Logging & Monitoring
- **Comprehensive error logging**
- **Processing status tracking**
- **Performance metrics**
- **Health check endpoints**

## Integration with UI

The service stores all data in your existing database, so you can:

1. **Query news directly** from the `news` table
2. **Filter by source** (portfolio vs watchlist)
3. **Sort by relevance** or publication date
4. **Display bullet points** for quick insights
5. **Show sentiment** for market mood
6. **Link to full articles** via stored URLs

## Troubleshooting

### Common Issues
1. **Missing API keys**: Check environment variables
2. **Database connection**: Verify DATABASE_URL
3. **Rate limiting**: Adjust delays in configuration
4. **Memory usage**: Monitor for large news content

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
python3 news_service.py
```

## Future Enhancements

- **News categorization** by sector/industry
- **Alert system** for breaking news
- **Historical analysis** and trends
- **Custom news sources** beyond Brave Search
- **Multi-user support** for different portfolios
- **News aggregation** from multiple sources
