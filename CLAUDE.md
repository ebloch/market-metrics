# CLAUDE.md - Market Metrics CLI Guide

## Commands
- **Run program**: `python market-metrics.py`
- **Run tests**: No test commands available yet
- **Install dependencies**: `pip install -r requirements.txt`
- **Set API Key**: `export FRED_API_KEY=your_api_key_here` (macOS/Linux) or `set FRED_API_KEY=your_api_key_here` (Windows)

## Code Style Guidelines
- **Imports**: Organize imports by standard library, external packages, then local modules
- **Type Hints**: Use typing module for all function signatures, e.g., `Dict[str, Any]`, `Optional[str]`
- **Naming**: Use snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Error Handling**: Use try/except blocks with specific exception types and descriptive error messages
- **Documentation**: Use docstrings for classes and functions with Args/Returns sections
- **Logging**: Use built-in logging module with appropriate log levels (info, warning, error)
- **Function Structure**: Private methods prefixed with underscore, e.g., `_log_error()`
- **Data Processing**: Use pandas for data manipulation, matplotlib for plotting

## Project Guidelines
- Financial data retrieved primarily from FRED API and Yahoo Finance
- Error handling should include cleanup of temporary files
- Use rich library for CLI output formatting and visual elements
- Maintain logging for all API calls and significant operations