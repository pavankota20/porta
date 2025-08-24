#!/usr/bin/env python3
"""
News Aggregation Service for Porta Finance
Fetches holdings from API, gets related news, processes through LLM, and stores in database
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import aiohttp
import asyncpg
from anthropic import Anthropic
import os
from dotenv import load_dotenv

# Import from existing config
from config import (
    ANTHROPIC_API_KEY, DATABASE_URL, PORTFOLIO_API_URL, 
    WATCHLIST_API_URL, DEFAULT_USER_ID, BRAVE_SEARCH_API_KEY,
    USER_PREFERENCES_API_URL
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    """Represents a news item with all necessary data including personalization"""
    news_id: str
    ticker: str
    title: str
    description: str
    url: str
    source: str
    published_at: datetime
    content: str
    bullet_points: List[str]
    sentiment: str
    relevance_score: float
    personalized_insights: str
    created_at: datetime
    updated_at: datetime

@dataclass
class PortfolioItem:
    """Represents a portfolio item from the portfolio API"""
    ticker: str
    user_id: str
    quantity: str
    buy_price: str
    note: Optional[str] = None

class NewsDatabase:
    """Database operations for news storage"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            await self.create_tables()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
    
    async def _get_connection(self):
        """Get a database connection with proper error handling"""
        try:
            if not self.pool:
                raise Exception("Database pool not initialized")
            return await self.pool.acquire()
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise
    
    async def create_tables(self):
        """Create necessary database tables"""
        async with self._lock:
            try:
                conn = await self._get_connection()
                try:
                    # News table with personalized insights
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS news (
                            news_id VARCHAR(255) PRIMARY KEY,
                            ticker VARCHAR(20) NOT NULL,
                            title TEXT NOT NULL,
                            description TEXT,
                            url TEXT NOT NULL,
                            source VARCHAR(100),
                            published_at TIMESTAMP,
                            content TEXT,
                            bullet_points JSONB,
                            sentiment VARCHAR(20),
                            relevance_score DECIMAL(3,2),
                            ticker_source VARCHAR(20) DEFAULT 'portfolio',
                            personalized_insights TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Portfolio table for caching
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS portfolio_cache (
                            ticker VARCHAR(20) PRIMARY KEY,
                            user_id VARCHAR(255),
                            quantity VARCHAR(50),
                            buy_price VARCHAR(50),
                            note TEXT,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Watchlist cache table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS watchlist_cache (
                            ticker VARCHAR(20) PRIMARY KEY,
                            user_id VARCHAR(255),
                            note TEXT,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # News processing status table
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS news_processing_status (
                            ticker VARCHAR(20) PRIMARY KEY,
                            last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_news_count INTEGER DEFAULT 0,
                            status VARCHAR(20) DEFAULT 'idle',
                            ticker_source VARCHAR(20) DEFAULT 'portfolio'
                        )
                    """)
                    
                    # Create indexes
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news(ticker)")
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at)")
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_news_created_at ON news(created_at)")
                    await conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker_source ON news(ticker_source)")
                    
                    logger.info("Database tables created successfully")
                finally:
                    await self.pool.release(conn)
            except Exception as e:
                logger.error(f"Failed to create tables: {e}")
                raise
    
    async def store_news(self, news_item: NewsItem, ticker_source: str = 'portfolio') -> bool:
        """Store a news item in the database"""
        try:
            conn = await self._get_connection()
            try:
                await conn.execute("""
                    INSERT INTO news (
                        news_id, ticker, title, description, url, source, 
                        published_at, content, bullet_points, sentiment, 
                        relevance_score, ticker_source, personalized_insights, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (news_id) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        content = EXCLUDED.content,
                        bullet_points = EXCLUDED.bullet_points,
                        sentiment = EXCLUDED.sentiment,
                        relevance_score = EXCLUDED.relevance_score,
                        ticker_source = EXCLUDED.ticker_source,
                        personalized_insights = EXCLUDED.personalized_insights
                """, 
                news_item.news_id, news_item.ticker, news_item.title, 
                news_item.description, news_item.url, news_item.source,
                news_item.published_at, news_item.content, 
                json.dumps(news_item.bullet_points), news_item.sentiment,
                news_item.relevance_score, ticker_source, news_item.personalized_insights, news_item.created_at, news_item.updated_at
                )
                return True
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to store news: {e}")
            return False
    
    async def store_watchlist_cache(self, watchlist_tickers: List[str], user_id: str):
        """Cache watchlist data"""
        try:
            conn = await self._get_connection()
            try:
                for ticker in watchlist_tickers:
                    await conn.execute("""
                        INSERT INTO watchlist_cache (ticker, user_id, last_updated)
                        VALUES ($1, $2, CURRENT_TIMESTAMP)
                        ON CONFLICT (ticker) DO UPDATE SET
                            last_updated = CURRENT_TIMESTAMP
                    """, ticker, user_id)
                logger.info(f"Cached {len(watchlist_tickers)} watchlist tickers")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to cache watchlist: {e}")
    
    async def get_watchlist_from_cache(self, user_id: str) -> List[str]:
        """Get watchlist tickers from cache"""
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch("""
                    SELECT ticker FROM watchlist_cache 
                    WHERE user_id = $1 AND last_updated > CURRENT_TIMESTAMP - INTERVAL '1 hour'
                """, user_id)
                return [row['ticker'] for row in rows]
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to get watchlist from cache: {e}")
            return []
    
    async def news_exists(self, news_id: str) -> bool:
        """Check if news item already exists"""
        try:
            conn = await self._get_connection()
            try:
                result = await conn.fetchval(
                    "SELECT 1 FROM news WHERE news_id = $1", news_id
                )
                return result is not None
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to check news existence: {e}")
            return False
    
    async def store_portfolio_cache(self, portfolios: List[PortfolioItem]):
        """Cache portfolio data"""
        try:
            conn = await self._get_connection()
            try:
                for portfolio in portfolios:
                    await conn.execute("""
                        INSERT INTO portfolio_cache (ticker, user_id, quantity, buy_price, note, last_updated)
                        VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                        ON CONFLICT (ticker) DO UPDATE SET
                            user_id = EXCLUDED.user_id,
                            quantity = EXCLUDED.quantity,
                            buy_price = EXCLUDED.buy_price,
                            note = EXCLUDED.note,
                            last_updated = CURRENT_TIMESTAMP
                    """, portfolio.ticker, portfolio.user_id, portfolio.quantity, 
                         portfolio.buy_price, portfolio.note)
                logger.info(f"Cached {len(portfolios)} portfolios")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to cache portfolios: {e}")
    
    async def get_portfolios_from_cache(self) -> List[PortfolioItem]:
        """Get portfolios from cache"""
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch("""
                    SELECT ticker, user_id, quantity, buy_price, note 
                    FROM portfolio_cache 
                    WHERE last_updated > CURRENT_TIMESTAMP - INTERVAL '1 hour'
                """)
                return [PortfolioItem(
                    ticker=row['ticker'],
                    user_id=row['user_id'],
                    quantity=row['quantity'],
                    buy_price=row['buy_price'],
                    note=row['note']
                ) for row in rows]
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to get portfolios from cache: {e}")
            return []
    
    async def update_processing_status(self, ticker: str, news_count: int, status: str = 'completed', ticker_source: str = 'portfolio'):
        """Update processing status for a ticker"""
        try:
            conn = await self._get_connection()
            try:
                await conn.execute("""
                    INSERT INTO news_processing_status (ticker, last_processed, last_news_count, status, ticker_source)
                    VALUES ($1, CURRENT_TIMESTAMP, $2, $3, $4)
                    ON CONFLICT (ticker) DO UPDATE SET
                        last_processed = CURRENT_TIMESTAMP,
                        last_news_count = $2,
                        status = $3,
                        ticker_source = $4
                """, ticker, news_count, status, ticker_source)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Failed to update processing status: {e}")

class NewsAPI:
    """Handles news API calls"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/news/search"
    
    async def search_news(self, ticker: str, count: int = 20) -> List[Dict[str, Any]]:
        """Search for news related to a ticker"""
        try:
            if not self.api_key:
                logger.error("No Brave Search API key configured")
                return []
                
            async with aiohttp.ClientSession() as session:
                # Build query exactly like the example - use valid parameters
                query = f"{ticker} stock"
                params = {
                    'q': query,
                    'count': count,
                    'search_lang': 'en',  # Fixed: use 'en' instead of 'en_US'
                    'country': 'US'
                }
                
                headers = {
                    'Accept': 'application/json',
                    'X-Subscription-Token': self.api_key
                }
                
                logger.info(f"Searching news for {ticker} with query: '{query}' and params: {params}")
                logger.info(f"Full URL: {self.base_url}?q={query}&count={count}")
                
                async with session.get(self.base_url, params=params, headers=headers, timeout=30) as response:
                    logger.info(f"News API response status for {ticker}: {response.status}")
                    logger.info(f"News API response headers: {dict(response.headers)}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"News API raw response for {ticker}: {data}")
                        
                        results = data.get('results', [])
                        logger.info(f"Found {len(results)} news items for {ticker}")
                        
                        # Log first result for debugging
                        if results:
                            first_result = results[0]
                            logger.info(f"First news result for {ticker}: {first_result}")
                        
                        return results
                    else:
                        response_text = await response.text()
                        logger.warning(f"News API returned status {response.status} for {ticker}")
                        logger.warning(f"News API error response: {response_text}")
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

class UserPreferencesAPI:
    """Handles user preferences API calls"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def fetch_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user preferences from API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{user_id}/"
                logger.info(f"Fetching user preferences from: {url}")
                
                async with session.get(url, timeout=30) as response:
                    logger.info(f"User Preferences API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"User preferences fetched: {data}")
                        return data
                    else:
                        response_text = await response.text()
                        logger.warning(f"User Preferences API returned status {response.status}: {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Failed to fetch user preferences: {e}")
            return None

class LLMProcessor:
    """Handles LLM processing of news content with user personalization"""
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-7-sonnet-20250219"
    
    def _create_personalized_prompt(self, title: str, description: str, content: str, ticker: str, user_prefs: Optional[Dict[str, Any]] = None) -> str:
        """Create a personalized prompt based on user preferences"""
        
        # Base prompt
        base_prompt = f"""You are a personalized financial analyst. Analyze this news article about {ticker} and provide insights tailored to the user's investment profile.

Title: {title}
Description: {description}
Content: {content[:1500]}  # Limit content length

You must respond with ONLY this exact JSON format, no other text:
{{
    "bullet_points": ["point1", "point2", "point3"],
    "sentiment": "positive",
    "relevance_score": 0.85,
    "reasoning": "brief explanation",
    "personalized_insights": "tailored insights based on user profile"
}}

Rules:
- bullet_points: exactly 3 key insights from the article
- sentiment: only "positive", "negative", or "neutral"
- relevance_score: number between 0.0 and 1.0
- reasoning: 1-2 sentence explanation
- personalized_insights: insights tailored to user's investment profile
- NO additional text, ONLY the JSON"""

        # Add personalization if user preferences are available
        if user_prefs:
            personalization_context = f"""

USER INVESTMENT PROFILE:
- Experience Level: {user_prefs.get('experience_level', 'intermediate')}
- Investment Style: {user_prefs.get('investment_style', 'moderate')}
- Risk Tolerance: {user_prefs.get('risk_tolerance', 'medium')}
- Communication Style: {user_prefs.get('communication_style', 'simple')}
- Preferred Sectors: {', '.join(user_prefs.get('preferred_sectors', []))}
- Investment Goals: {', '.join(user_prefs.get('investment_goals', []))}
- Preferred Timeframe: {user_prefs.get('preferred_timeframe', 'medium_term')}
- Preferred Asset Classes: {', '.join(user_prefs.get('preferred_asset_classes', []))}

PERSONALIZATION INSTRUCTIONS:
- Adjust complexity based on experience level (beginner=simple, expert=technical)
- Consider risk tolerance when analyzing impact
- Focus on sectors and asset classes the user prefers
- Align insights with their investment goals and timeframe
- Use communication style appropriate for their preference
- Highlight aspects most relevant to their investment strategy"""
            
            base_prompt += personalization_context
        
        return base_prompt
    
    async def process_news_content(self, title: str, description: str, content: str, ticker: str, user_prefs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process news content through LLM to generate personalized bullet points and sentiment"""
        try:
            # Create personalized prompt
            prompt = self._create_personalized_prompt(title, description, content, ticker, user_prefs)
            
            logger.info(f"Processing news for {ticker} with personalized LLM...")
            if user_prefs:
                logger.info(f"Using user preferences: {user_prefs.get('experience_level', 'N/A')} level, {user_prefs.get('risk_tolerance', 'N/A')} risk tolerance")
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=400,  # Increased for personalized insights
                temperature=0.1,  # Lower temperature for more consistent JSON
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            logger.info(f"LLM raw response for {ticker}: {response_text[:200]}...")
            
            # Try to extract JSON from the response
            try:
                # Look for JSON content between curly braces
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                
                if start != -1 and end != 0:
                    json_text = response_text[start:end]
                    logger.info(f"Extracted JSON for {ticker}: {json_text}")
                    
                    result = json.loads(json_text)
                    
                    # Validate the response
                    bullet_points = result.get('bullet_points', [])
                    sentiment = result.get('sentiment', 'neutral')
                    relevance_score = result.get('relevance_score', 0.5)
                    reasoning = result.get('reasoning', '')
                    personalized_insights = result.get('personalized_insights', '')
                    
                    # Ensure we have exactly 3 bullet points
                    if len(bullet_points) < 3:
                        bullet_points.extend([f"Additional insight about {ticker}", "Market analysis", "Investment consideration"])
                    elif len(bullet_points) > 3:
                        bullet_points = bullet_points[:3]
                    
                    # Validate sentiment
                    if sentiment not in ['positive', 'negative', 'neutral']:
                        sentiment = 'neutral'
                    
                    # Validate relevance score
                    try:
                        relevance_score = float(relevance_score)
                        if not (0.0 <= relevance_score <= 1.0):
                            relevance_score = 0.5
                    except (ValueError, TypeError):
                        relevance_score = 0.5
                    
                    return {
                        'bullet_points': bullet_points,
                        'sentiment': sentiment,
                        'relevance_score': relevance_score,
                        'reasoning': reasoning,
                        'personalized_insights': personalized_insights
                    }
                else:
                    logger.warning(f"No JSON found in LLM response for {ticker}")
                    raise ValueError("No JSON content found")
                    
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse LLM response for {ticker}: {e}")
                logger.warning(f"Full response: {response_text}")
                
                # Generate fallback response
                return {
                    'bullet_points': [
                        f"News about {ticker} stock performance",
                        "Financial market update and analysis", 
                        "Investment opportunity assessment"
                    ],
                    'sentiment': 'neutral',
                    'relevance_score': 0.5,
                    'reasoning': f'Fallback response for {ticker} due to LLM parsing error',
                    'personalized_insights': f'Standard analysis for {ticker} - user preferences not available'
                }
                
        except Exception as e:
            logger.error(f"LLM processing failed for {ticker}: {e}")
            import traceback
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            
            return {
                'bullet_points': [
                    f"News about {ticker} stock",
                    "Financial market update", 
                    "Investment information"
                ],
                'sentiment': 'neutral',
                'relevance_score': 0.5,
                'reasoning': f'Fallback response for {ticker} due to LLM processing error',
                'personalized_insights': f'Standard analysis for {ticker} - processing error occurred'
            }

class HoldingsAPI:
    """Handles portfolio API calls"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    async def fetch_portfolio(self, user_id: str) -> List[PortfolioItem]:
        """Fetch portfolio holdings from portfolio API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{user_id}/holdings"
                logger.info(f"Fetching portfolio from: {url}")
                
                async with session.get(url, timeout=30) as response:
                    logger.info(f"Portfolio API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Portfolio API response: {data}")
                        
                        portfolios = []
                        for item in data.get('holdings', []):
                            portfolios.append(PortfolioItem(
                                ticker=item.get('ticker', ''),
                                user_id=user_id,
                                quantity=item.get('quantity', ''),
                                buy_price=item.get('buy_price', ''),
                                note=item.get('note')
                            ))
                        
                        logger.info(f"Parsed {len(portfolios)} portfolio holdings: {[p.ticker for p in portfolios]}")
                        return portfolios
                    else:
                        logger.warning(f"Portfolio API returned status {response.status}")
                        response_text = await response.text()
                        logger.warning(f"Portfolio API response: {response_text}")
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch portfolio: {e}")
            return []
    
    async def fetch_watchlist(self, user_id: str) -> List[str]:
        """Fetch watchlist tickers from watchlist API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{WATCHLIST_API_URL}{user_id}/"
                logger.info(f"Fetching watchlist from: {url}")
                
                async with session.get(url, timeout=30) as response:
                    logger.info(f"Watchlist API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Watchlist API response: {data}")
                        
                        watchlist = []
                        for item in data.get('watchlist', []):
                            ticker = item.get('ticker', '')
                            if ticker:
                                watchlist.append(ticker)
                        
                        logger.info(f"Parsed {len(watchlist)} watchlist items: {watchlist}")
                        return watchlist
                    else:
                        logger.warning(f"Watchlist API returned status {response.status}")
                        response_text = await response.text()
                        logger.warning(f"Watchlist API response: {response_text}")
                        return []
        except Exception as e:
            logger.error(f"Failed to fetch watchlist: {e}")
            return []

class NewsAggregator:
    """Main news aggregation service with user personalization"""
    
    def __init__(self):
        self.db = NewsDatabase(DATABASE_URL)
        self.news_api = NewsAPI(BRAVE_SEARCH_API_KEY)
        self.llm = LLMProcessor(ANTHROPIC_API_KEY)
        self.portfolio_api = HoldingsAPI(PORTFOLIO_API_URL)
        self.user_prefs_api = UserPreferencesAPI(USER_PREFERENCES_API_URL)
        self.user_id = DEFAULT_USER_ID
        self.running = False
        self.user_preferences = None
    
    async def start(self):
        """Start the news aggregator service"""
        try:
            await self.db.connect()
            
            # Fetch user preferences on startup
            await self._load_user_preferences()
            
            self.running = True
            logger.info("News aggregator service started")
            
            # Start the scheduler in the same event loop
            asyncio.create_task(self._run_scheduler())
            
            # Keep the main thread alive
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start news aggregator: {e}")
            raise
        finally:
            await self.db.close()
    
    async def _load_user_preferences(self):
        """Load user preferences for personalization"""
        try:
            logger.info(f"Loading user preferences for user: {self.user_id}")
            self.user_preferences = await self.user_prefs_api.fetch_user_preferences(self.user_id)
            
            if self.user_preferences:
                logger.info(f"✅ User preferences loaded successfully")
                logger.info(f"   Experience Level: {self.user_preferences.get('experience_level', 'N/A')}")
                logger.info(f"   Risk Tolerance: {self.user_preferences.get('risk_tolerance', 'N/A')}")
                logger.info(f"   Investment Style: {self.user_preferences.get('investment_style', 'N/A')}")
                logger.info(f"   Preferred Sectors: {', '.join(self.user_preferences.get('preferred_sectors', []))}")
            else:
                logger.warning("⚠️  No user preferences found, using default analysis")
                
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")
            self.user_preferences = None
    
    async def _run_scheduler(self):
        """Run the scheduler in the same event loop"""
        while self.running:
            try:
                # Process news batch
                await self._process_news_batch()
                
                # Wait 30 seconds before next run
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds on error before retrying
    
    async def _process_news_batch(self):
        """Process news for all holdings AND watchlist items in a batch"""
        try:
            logger.info("Starting news batch processing")
            
            # Get all tickers we need to process (holdings + watchlist)
            portfolio_tickers = set()
            watchlist_tickers = set()
            
            # Fetch holdings from API
            portfolios = await self.portfolio_api.fetch_portfolio(self.user_id)
            if portfolios:
                for portfolio in portfolios:
                    portfolio_tickers.add(portfolio.ticker)
                # Cache holdings
                await self.db.store_portfolio_cache(portfolios)
                logger.info(f"Found {len(portfolios)} portfolio holdings")
            else:
                logger.warning("No portfolios found, using cached data")
                cached_portfolios = await self.db.get_portfolios_from_cache()
                for portfolio in cached_portfolios:
                    portfolio_tickers.add(portfolio.ticker)
                
                # If still no portfolios, use test data
                if not portfolio_tickers:
                    logger.info("No cached portfolios, using test data")
                    portfolio_tickers = {'AAPL', 'GOOGL', 'MSFT', 'TSLA'}
            
            # Fetch watchlist
            watchlist_tickers = await self.portfolio_api.fetch_watchlist(self.user_id)
            if watchlist_tickers:
                # Cache watchlist
                await self.db.store_watchlist_cache(watchlist_tickers, self.user_id)
                logger.info(f"Found {len(watchlist_tickers)} watchlist items")
            else:
                logger.warning("No watchlist found, using cached data")
                cached_watchlist = await self.db.get_watchlist_from_cache(self.user_id)
                watchlist_tickers = set(cached_watchlist)
                
                # If still no watchlist, use test data
                if not watchlist_tickers:
                    logger.info("No cached watchlist, using test data")
                    watchlist_tickers = {'AMZN', 'META', 'NVDA'}
            
            # Combine all tickers
            all_tickers = portfolio_tickers.union(watchlist_tickers)
            
            if not all_tickers:
                logger.warning("No tickers available for news processing")
                return
            
            logger.info(f"Processing news for {len(all_tickers)} total tickers")
            logger.info(f"Portfolio tickers: {', '.join(sorted(portfolio_tickers))}")
            logger.info(f"Watchlist tickers: {', '.join(sorted(watchlist_tickers))}")
            
            # Process news for portfolio tickers
            for ticker in sorted(portfolio_tickers):
                await self._process_news_for_ticker(ticker, 'portfolio')
                await asyncio.sleep(1)  # Rate limiting
            
            # Process news for watchlist tickers
            for ticker in sorted(watchlist_tickers):
                await self._process_news_for_ticker(ticker, 'watchlist')
                await asyncio.sleep(1)  # Rate limiting
            
            logger.info("News batch processing completed")
            
        except Exception as e:
            logger.error(f"News batch processing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _process_news_for_ticker(self, ticker: str, ticker_source: str = 'portfolio'):
        """Process news for a specific ticker"""
        try:
            logger.info(f"Processing news for {ticker} (source: {ticker_source})")
            
            # Fetch news from API
            news_items = await self.news_api.search_news(ticker, count=15)
            
            if not news_items:
                logger.info(f"No news found for {ticker}")
                await self.db.update_processing_status(ticker, 0, 'completed', ticker_source)
                return
            
            processed_count = 0
            
            for news_data in news_items:
                # Generate unique news ID
                news_id = self._generate_news_id(news_data)
                
                # Check if news already exists
                if await self.db.news_exists(news_id):
                    continue
                
                # Process content through LLM
                llm_result = await self.llm.process_news_content(
                    news_data.get('title', ''),
                    news_data.get('description', ''),
                    news_data.get('content', ''),
                    ticker,
                    self.user_preferences # Pass user preferences to LLM
                )
                
                # Create news item
                news_item = NewsItem(
                    news_id=news_id,
                    ticker=ticker,
                    title=news_data.get('title', ''),
                    description=news_data.get('description', ''),
                    url=news_data.get('url', ''),
                    source=news_data.get('source', ''),
                    published_at=datetime.fromisoformat(news_data.get('published', datetime.now().isoformat())),
                    content=news_data.get('content', ''),
                    bullet_points=llm_result['bullet_points'],
                    sentiment=llm_result['sentiment'],
                    relevance_score=llm_result['relevance_score'],
                    personalized_insights=llm_result['personalized_insights'],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # Store in database with source
                if await self.db.store_news(news_item, ticker_source):
                    processed_count += 1
                
                # Rate limiting for LLM calls
                await asyncio.sleep(0.5)
            
            await self.db.update_processing_status(ticker, processed_count, 'completed', ticker_source)
            logger.info(f"Processed {processed_count} news items for {ticker} ({ticker_source})")
            
        except Exception as e:
            logger.error(f"Failed to process news for {ticker}: {e}")
            await self.db.update_processing_status(ticker, 0, 'error', ticker_source)
    
    def _generate_news_id(self, news_data: Dict[str, Any]) -> str:
        """Generate a unique news ID based on content"""
        content = f"{news_data.get('title', '')}{news_data.get('url', '')}{news_data.get('published', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    async def stop(self):
        """Stop the news aggregator service"""
        self.running = False
        logger.info("News aggregator service stopped")

async def main():
    """Main entry point"""
    aggregator = NewsAggregator()
    
    try:
        await aggregator.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        await aggregator.stop()

async def test_news_api():
    """Test function to verify news API is working"""
    try:
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if not api_key:
            print("❌ No BRAVE_SEARCH_API_KEY found in environment")
            return False
            
        news_api = NewsAPI(api_key)
        print("🔍 Testing news API with GOOG...")
        
        results = await news_api.search_news("GOOG", count=2)
        
        if results:
            print(f"✅ Success! Found {len(results)} news items")
            for i, result in enumerate(results[:2]):
                print(f"  {i+1}. {result.get('title', 'No title')}")
                print(f"     Source: {result.get('source', 'Unknown')}")
                print(f"     URL: {result.get('url', 'No URL')}")
                print()
            return True
        else:
            print("❌ No news results returned")
            return False
            
    except Exception as e:
        print(f"❌ Error testing news API: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Test the news API first
    print("🧪 Testing News API...")
    test_success = asyncio.run(test_news_api())
    
    if test_success:
        print("✅ News API test passed, starting service...")
        asyncio.run(main())
    else:
        print("❌ News API test failed, check your configuration")
        exit(1)
