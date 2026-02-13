# Market Metrics CLI

A command-line interface tool for retrieving and analyzing market metrics data.

<img width="917" height="524" alt="image" src="https://github.com/user-attachments/assets/7ae91353-2ff8-4e3c-9ba0-5656be67d79f" />


## Dependencies

This tool requires Python 3.6 or higher and the following Python packages:

- requests
- pandas
- matplotlib
- argparse
- tabulate
- yfinance
- fredapi
- rich
- questionary

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/ebloch/market-metrics.git
   cd market-metrics
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

   Alternatively, you can install the dependencies manually:
   ```
   pip install requests pandas matplotlib argparse tabulate yfinance fredapi rich questionary
   ```

## API Key Setup

This tool requires a FRED (Federal Reserve Economic Data) API key to access economic data.

### Getting a FRED API Key

1. Visit the [FRED API Key Request Page](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Click on "Request API Key" button
3. If you don't have a FRED account, you'll need to create one
4. Fill out the form with your information and submit
5. You'll receive your API key via email or on the website

### Setting Up Your API Key

You need to set the FRED API key as an environment variable before running the application.

#### On macOS/Linux:

For temporary use in current terminal session:
```
export FRED_API_KEY=your_api_key_here
```

For permanent use, add to your shell profile file (~/.bashrc, ~/.zshrc, etc.):
```
echo 'export FRED_API_KEY=your_api_key_here' >> ~/.bashrc
source ~/.bashrc
```

#### On Windows:

Command Prompt (temporary, for current session only):
```
set FRED_API_KEY=your_api_key_here
```

PowerShell (temporary, for current session only):
```
$env:FRED_API_KEY = "your_api_key_here"
```

To set permanently via System Properties:
1. Search for "Environment Variables" in the Start menu
2. Click "Edit the system environment variables"
3. Click "Environment Variables" button
4. Under "User variables", click "New"
5. Variable name: `FRED_API_KEY`
6. Variable value: your API key
7. Click OK on all dialogs

## Usage

```
python market-metrics.py [options]
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--help` | Show help message with all options and usage information |
| `--export PATH` | Export all metrics to CSV file and exit (non-interactive) |
| `--test` | Run with dummy data for UI testing |

### Examples

```bash
# Launch interactive dashboard
python market-metrics.py

# Export metrics to CSV (for cron jobs or scripts)
python market-metrics.py --export daily_metrics.csv

# Test UI with dummy data (no API calls)
python market-metrics.py --test

# View full help
python market-metrics.py --help
```

### Dashboard Keys

When running the interactive dashboard:

| Key | Action |
|-----|--------|
| `1` | Export all metrics to CSV file |
| `2` | Plot a single FRED data series |
| `3` | Plot multiple FRED series for comparison |
| `S` | View data sources and timestamps |
| `R` | Refresh all market data |
| `Q` | Quit the application |

### Exit Codes (--export mode)

| Code | Meaning |
|------|---------|
| `0` | Success - all or some metrics exported |
| `1` | Failure - missing API key, invalid path, or all exports failed |

## Available Metrics

| Category | Metrics |
|----------|---------|
| **US Economy** | GDP, GDP Growth, Debt/GDP, Deficit, Inflation, Earnings Growth |
| **Valuations** | US P/E, Japan P/E, CAPE Ratio, Equity Risk Premium, Buffett Indicator |
| **Rates & Credit** | 10-Year Treasury Yield, BAA Credit Spread |
| **Assets** | Gold, Bitcoin, WTI Crude Oil |

## Data Sources

| Source | Data Provided |
|--------|---------------|
| FRED API | GDP, Inflation, Treasury Yields, Credit Spreads, Debt/Deficit |
| Yahoo Finance | P/E Ratios, Gold, Bitcoin, Oil prices, Market Cap |
| Robert Shiller | CAPE Ratio (Cyclically Adjusted P/E) |
| NYU Stern | Equity Risk Premium |

