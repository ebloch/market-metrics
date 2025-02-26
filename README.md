# Market Metrics CLI

A command-line interface tool for retrieving and analyzing market metrics data.

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
   git clone https://github.com/yourusername/market-metrics.git
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

## Usage

The basic syntax for using the CLI is:
```
python market-metrics.py
```

This will launch an interactive menu where you can select various market metrics to view.

## Available Metrics

- US P/E Ratio
- US CAPE Ratio
- US Credit Spreads
- US Stock Market / GDP
- US GDP
- US Government Debt & Deficit
- US 10-Year Yield
- US Inflation Rate
- US Equity Risk Premium
- US Earnings Growth
- Gold Price
- Bitcoin Price
- WTI Crude Oil Price

You can also export all metrics to CSV or plot historical data for any FRED series.

