# Porta - Finance Assistant

A clean, modular finance assistant built with LangChain and Anthropic Claude.

## Project Structure

```
porta/
├── porta/                    # Main package
│   ├── tools/               # Tool implementations
│   │   ├── portfolio.py     # Portfolio management tools
│   │   ├── watchlist.py     # Watchlist management tools
│   │   ├── web_search.py    # Web search tools (test implementation)
│   │   └── __init__.py      # Tools module exports
│   ├── agents/              # Agent implementations
│   │   ├── agent_builder.py # Agent creation logic
│   │   ├── interactive_runner.py # Interactive mode
│   │   ├── test_runner.py   # Testing utilities
│   │   └── __init__.py      # Agents module exports
│   └── utils/               # Utility functions
├── main.py                  # Main entry point
├── requirements.txt          # Dependencies
└── README.md               # This file
```

## Features

- **Portfolio Management**: Add, remove, and list portfolio holdings
- **Watchlist Management**: Add, remove, and list watchlist tickers
- **Web Search**: Search for financial information (test implementation)
- **Modular Design**: Clean separation of concerns for easy development

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   export ANTHROPIC_API_KEY="your_api_key_here"
   # or create a .env file
   ```

3. **Run interactive mode**:
   ```bash
   python main.py
   ```

4. **Run tests**:
   ```bash
   python main.py test
   ```

## Development

### Adding New Tools

1. Create a new file in `porta/tools/` (e.g., `new_tool.py`)
2. Define your tool function with the `@tool` decorator
3. Import it in `porta/tools/__init__.py`
4. Add it to the `TOOLS` list

### Adding New Agents

1. Create a new file in `porta/agents/` (e.g., `new_agent.py`)
2. Import it in `porta/agents/__init__.py`
3. Use it in your main application

## Example Commands

- `add AAPL to my watchlist`
- `put MSFT in my portfolio`
- `list my portfolio`
- `search for Tesla stock news`
- `web search for market trends`

## Architecture

- **Tools**: Individual functions that perform specific tasks
- **Agents**: LLM-powered coordinators that decide which tools to use
- **Executor**: Orchestrates tool calls and manages conversation flow

## Next Steps

- Integrate real web search API in `porta/tools/web_search.py`
- Add database persistence for portfolios and watchlists
- Implement user authentication and multi-user support
- Add more financial data tools (stock quotes, news, etc.)
