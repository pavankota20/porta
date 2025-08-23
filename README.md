# Porta - Finance Assistant

A clean, modular finance assistant built with LangChain and Anthropic Claude.

## Project Structure

```
porta/
├── agent.py                 # Main chatbot agent (entry point)
├── requirements.txt          # Python dependencies
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── docs/                   # Documentation files
│   ├── Everyday Investor Agent.pdf
│   └── Porta – Chatbot Capabilities & Data Model (build Spec V0.pdf
└── porta_env/              # Virtual environment (created by setup)
```

## Features

- **Portfolio Management**: Add, remove, and list portfolio holdings
- **Watchlist Management**: Add, remove, and list watchlist tickers  
- **Web Search**: Search for financial information (test implementation)
- **News Fetching**: Get finance-focused news headlines for specific tickers using Brave Search API
- **Modular Design**: Clean separation of concerns for easy development
- **Interactive Chat**: Natural language interface for managing finances

## Quick Start

### 1. Create Virtual Environment
```bash
# Create a new virtual environment
python -m venv porta_env

# Activate the virtual environment
# On macOS/Linux:
source porta_env/bin/activate
# On Windows:
# porta_env\Scripts\activate
```

### 2. Install Dependencies
```bash
# Make sure virtual environment is activated
pip install -r requirements.txt
```

### 3. Set up Environment Variables
```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your_api_key_here"

# Or create a .env file with:
# ANTHROPIC_API_KEY=your_api_key_here
```

### 4. Run the Chatbot
```bash
# Run interactive mode
python agent.py

# Run test mode
python agent.py test
```

## Usage Examples

Once running, you can interact with Porta using natural language:

- `add AAPL to my watchlist`
- `put MSFT in my portfolio with 10% weight`
- `list my portfolio`
- `remove AAPL from watchlist`
- `search for Tesla stock news`
- `web search for market trends`
- `get news for AAPL`
- `get news for MSFT last 7 days`

## Dependencies

The project uses the following key packages:
- **langchain-anthropic**: LangChain integration with Anthropic Claude
- **anthropic**: Official Anthropic API client
- **pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for API calls (used by get_news tool)

## get_news Tool

The `get_news` tool fetches finance-focused news headlines for specific stock tickers using the Brave Search API.

### Features
- **Finance-focused queries**: Automatically filters for earnings, guidance, investigations, outlook, forecasts, revenue, profit, acquisitions, and probes
- **Major finance sources**: Restricts results to reputable finance sites like Reuters, Bloomberg, WSJ, CNBC, and others
- **Smart ranking**: Results are ranked by recency, source authority, and presence of risk terms
- **Deduplication**: Removes duplicate news items by URL and title similarity
- **Caching**: Results are cached for reuse to improve performance
- **Configurable lookback**: Supports 1-30 day lookback periods

### Setup
To use the get_news tool, you need a Brave Search API key:

```bash
# Set your Brave Search API key
export BRAVE_API_KEY="your_brave_api_key_here"

# Or add to your .env file:
# BRAVE_API_KEY=your_brave_api_key_here
```

### API Response Format
The tool returns news items in this format:
```json
{
  "ok": true,
  "ticker": "AAPL",
  "lookback_days": 3,
  "items": [
    {
      "ticker": "AAPL",
      "title": "Apple Reports Strong Q4 Earnings",
      "url": "https://example.com/article",
      "source": "Reuters",
      "snippet": "Apple Inc reported quarterly earnings...",
      "published_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

## Development

### Project Architecture

- **`agent.py`**: Main chatbot implementation with all tools integrated
- **Tools**: Portfolio, watchlist, and web search functionality
- **LangChain Integration**: Uses LangChain's tool calling framework
- **In-Memory Storage**: Currently uses Python dictionaries (can be extended to databases)

### Adding New Features

1. **New Tools**: Add functions with `@tool` decorator in `agent.py`
2. **New Commands**: Extend the system prompt and tool list
3. **Persistence**: Replace in-memory storage with database solutions

## Environment Setup

### Prerequisites
- Python 3.9+
- Anthropic API key (get from [console.anthropic.com](https://console.anthropic.com))

### Virtual Environment Management
```bash
# Activate
source porta_env/bin/activate

# Deactivate
deactivate

# Remove environment (if needed)
rm -rf porta_env
```

## Testing

The chatbot includes a test mode to verify all tools work correctly:

```bash
python agent.py test
```

This will run through example commands to ensure:
- Portfolio management tools work
- Watchlist management tools work  
- Web search tool responds correctly
- Agent can properly call tools

## Next Steps

- [ ] Integrate real web search API (currently test implementation)
- [ ] Add database persistence for portfolios and watchlists
- [ ] Implement user authentication and multi-user support
- [ ] Add real-time stock data integration
- [ ] Create web interface
- [ ] Add more financial analysis tools

## Troubleshooting

### Common Issues

1. **API Key Not Set**: Make sure `ANTHROPIC_API_KEY` is set in environment
2. **Virtual Environment Not Activated**: Ensure `porta_env` is activated before running
3. **Dependencies Not Installed**: Run `pip install -r requirements.txt` in activated environment

### Getting Help

- Check that your virtual environment is activated
- Verify your Anthropic API key is valid
- Ensure all dependencies are installed correctly
