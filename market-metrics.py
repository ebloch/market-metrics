import yfinance as yf
import fredapi
import pandas as pd
import requests
from datetime import datetime, timedelta
import os
from typing import Dict, Any, List, Optional
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import questionary
from rich.live import Live
from rich.spinner import Spinner
import time
import logging
import importlib
import sys
import subprocess
import csv

class USMarketMetrics:
    def __init__(self, fred_api_key: str, csv_export_path: Optional[str] = None):
        """
        Initialize with FRED API key
        Get it from: https://fred.stlouisfed.org/docs/api/api_key.html
        
        Args:
            fred_api_key: API key for FRED
            csv_export_path: Optional path to export data as CSV
        """
        self.fred = fredapi.Fred(api_key=fred_api_key)
        self.csv_export_path = csv_export_path
        self.csv_headers_written = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("market_metrics.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('USMarketMetrics')
        
        # Check for required dependencies
        self._check_dependencies()
        
        # Initialize CSV file if export path is provided
        if self.csv_export_path:
            self._initialize_csv_export()
        
    def _check_dependencies(self):
        """Check if all required dependencies are installed"""
        dependencies = [
            ('xlrd', 'xlrd>=2.0.1', 'Excel files'),
            ('openpyxl', 'openpyxl>=3.0.0', 'modern Excel files')
        ]
        
        for module_name, install_spec, description in dependencies:
            try:
                importlib.import_module(module_name)
                self.logger.info(f"{module_name} dependency is installed")
            except ImportError:
                self.logger.warning(f"Missing {module_name} dependency. Attempting to install...")
                print(f"\n[bold yellow]Missing {module_name} dependency required for {description}.[/bold yellow]")
                
                try:
                    # Try to install dependency
                    subprocess.check_call([sys.executable, "-m", "pip", "install", install_spec])
                    self.logger.info(f"Successfully installed {module_name}")
                    print(f"[bold green]Successfully installed {module_name} dependency.[/bold green]")
                except Exception as e:
                    self.logger.error(f"Failed to install {module_name}: {str(e)}")
                    print(f"[bold red]Failed to automatically install {module_name}.[/bold red]")
                    print(f"Please install it manually with: pip install {install_spec}")
    
    def _initialize_csv_export(self):
        """Initialize the CSV export file with headers"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.csv_export_path)), exist_ok=True)
            
            # Check if file exists and is empty
            file_exists = os.path.isfile(self.csv_export_path)
            file_empty = not file_exists or os.path.getsize(self.csv_export_path) == 0
            
            if file_empty:
                self.logger.info(f"Initializing CSV export file at {self.csv_export_path}")
                # We'll write headers when the first data is exported
            else:
                self.logger.info(f"CSV export file already exists at {self.csv_export_path}")
                self.csv_headers_written = True
                
        except Exception as e:
            self.logger.error(f"Error initializing CSV export: {str(e)}", exc_info=True)
            print(f"[bold red]Error initializing CSV export: {str(e)}[/bold red]")
            self.csv_export_path = None  # Disable CSV export on error
    
    def _export_to_csv(self, metric_name: str, data: Dict[str, Any]):
        """Export metric data to CSV file"""
        if not self.csv_export_path:
            return
            
        try:
            # Make a deep copy to avoid modifying the original data
            data_copy = data.copy()
            
            # Extract metadata
            timestamp = data_copy.pop('timestamp') if 'timestamp' in data_copy else datetime.now().strftime('%Y-%m-%d')
            source = data_copy.pop('source') if 'source' in data_copy else 'Unknown'
            
            # Prepare rows for CSV
            rows_to_write = []
            
            # Handle different data structures
            if len(data_copy) == 1 and 'value' in data_copy:
                # Single value metric (like P/E ratio)
                row = {
                    'metric': metric_name,
                    'sub_metric': 'value',
                    'value': data_copy['value'],
                    'timestamp': timestamp,
                    'source': source,
                    'retrieval_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                rows_to_write.append(row)
            else:
                # Multiple value metrics (like GDP or Government Debt)
                for key, value in data_copy.items():
                    if isinstance(value, dict):
                        # Handle nested dictionaries (like credit_spreads)
                        for sub_key, sub_value in value.items():
                            row = {
                                'metric': metric_name,
                                'sub_metric': f"{key}_{sub_key}",
                                'value': sub_value,
                                'timestamp': timestamp,
                                'source': source,
                                'retrieval_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            rows_to_write.append(row)
                    else:
                        # Handle flat key-value pairs
                        row = {
                            'metric': metric_name,
                            'sub_metric': key,
                            'value': value,
                            'timestamp': timestamp,
                            'source': source,
                            'retrieval_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        rows_to_write.append(row)
            
            # Write to CSV
            file_exists = os.path.isfile(self.csv_export_path) and os.path.getsize(self.csv_export_path) > 0
            
            with open(self.csv_export_path, mode='a', newline='') as file:
                fieldnames = ['metric', 'sub_metric', 'value', 'timestamp', 'source', 'retrieval_time']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                # Write headers if this is the first write
                if not file_exists or not self.csv_headers_written:
                    writer.writeheader()
                    self.csv_headers_written = True
                
                # Write all rows
                for row in rows_to_write:
                    writer.writerow(row)
                
            self.logger.info(f"Exported {metric_name} data to CSV with {len(rows_to_write)} rows")
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {str(e)}", exc_info=True)
            print(f"[bold red]Error exporting to CSV: {str(e)}[/bold red]")
    
    def get_pe_ratio(self) -> float:
        """
        Get current US stock market P/E ratio
        
        Uses VTI (Vanguard Total Stock Market ETF) as a proxy for the entire US market
        """
        return self._get_ticker_info("VTI", "P/E ratio", "trailingPE")
    
    def _get_ticker_info(self, symbol: str, description: str, info_field: str) -> float:
        """Get ticker information from Yahoo Finance"""
        try:
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Get requested info
            value = ticker.info.get(info_field)
            print(f"\nFetching US stock market {description} ({symbol})")
            
            if value:
                print(f"Found {description}: {value}")
                return float(value)
            
            print(f"No {description} data available")
            return None
        except Exception as e:
            return self._log_error(f"fetching {description}", e)
    
    def get_cape_ratio(self) -> float:
        """
        Get current Cyclically Adjusted P/E (CAPE) ratio for the US market
        
        Uses Robert Shiller's data from his website
        """
        try:
            # URL for Shiller's data
            url = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
            self.logger.info(f"Fetching CAPE ratio from Shiller's dataset: {url}")
            print(f"\nFetching CAPE ratio from Shiller's dataset")
            
            if not self._download_file(url, "shiller_temp.xls"):
                return None
            
            # Read the Excel file
            df = pd.read_excel("shiller_temp.xls", sheet_name="Data", skiprows=7)
            
            # Get the most recent CAPE value (column 'CAPE')
            # Column names may vary, so find the CAPE column
            cape_column = None
            for col in df.columns:
                if 'CAPE' in str(col).upper():
                    cape_column = col
                    break
                
            if not cape_column:
                self.logger.error("Could not find CAPE column in Shiller's data")
                raise Exception("Could not find CAPE column in the data")
            
            # Get the most recent non-NaN value
            cape_value = df[cape_column].dropna().iloc[-1]
            
            # Log the result
            self.logger.info(f"Found CAPE ratio: {cape_value}")
            print(f"Found CAPE ratio: {cape_value}")
            
            # Clean up temp file
            if os.path.exists("shiller_temp.xls"):
                os.remove("shiller_temp.xls")
            
            return float(cape_value)
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists("shiller_temp.xls"):
                os.remove("shiller_temp.xls")
            
            return self._log_error("fetching CAPE ratio", e)
    
    def _get_cape_from_fred(self) -> float:
        """Fallback method to get CAPE ratio from FRED"""
        try:
            self.logger.info("Falling back to FRED for CAPE ratio")
            print("Falling back to FRED for CAPE ratio")
            
            # Get CAPE ratio from FRED (series ID: MULTPL/SHILLER_PE_RATIO_MONTH)
            cape_series = self.fred.get_series('MULTPL/SHILLER_PE_RATIO_MONTH')
            
            if cape_series is not None and not cape_series.empty:
                cape_ratio = cape_series.iloc[-1]
                self.logger.info(f"Found CAPE ratio from FRED: {cape_ratio}")
                print(f"Found CAPE ratio from FRED: {cape_ratio}")
                return float(cape_ratio)
            
            self.logger.warning("Could not get CAPE ratio from FRED")
            print("Could not get CAPE ratio from FRED")
            return None
        except Exception as e:
            return self._log_error("fetching CAPE ratio from FRED", e)
    
    def get_credit_spreads(self) -> Dict[str, float]:
        """Get credit spreads (BAA corporate bond yield - 10-year Treasury yield)"""
        try:
            print(f"\nFetching credit spreads")
            
            # Get BAA corporate bond yield
            baa_yield = self._safe_get_fred_series('BAA')
            
            # Get 10-year Treasury yield
            treasury_10y = self._safe_get_fred_series('DGS10')
            
            if baa_yield is None or treasury_10y is None or baa_yield.empty or treasury_10y.empty:
                return {'baa_yield': None, 'treasury_10y': None, 'baa_spread': None}
            
            # Get the most recent values
            latest_baa = baa_yield.iloc[-1]
            latest_10y = treasury_10y.iloc[-1]
            
            # Calculate the spread
            spread = latest_baa - latest_10y
            
            self.logger.info(f"Found BAA yield: {latest_baa:.2f}%, 10-year Treasury: {latest_10y:.2f}%, Spread: {spread:.2f}%")
            print(f"BAA Corporate Bond Yield: {latest_baa:.2f}%")
            print(f"10-Year Treasury Yield: {latest_10y:.2f}%")
            print(f"Credit Spread: {spread:.2f}% ({int(spread*100)} basis points)")
            
            return {
                'baa_yield': float(latest_baa),
                'treasury_10y': float(latest_10y),
                'baa_spread': float(spread)
            }
        except Exception as e:
            return self._log_error("calculating credit spreads", e)
    
    def get_market_to_gdp(self) -> float:
        """Get US stock market capitalization to GDP ratio (Buffett Indicator)"""
        try:
            print(f"\nFetching US stock market to GDP ratio")
            
            # Get market cap to GDP from FRED (DDDM01USA156NWDB)
            market_to_gdp = self._safe_get_fred_series('DDDM01USA156NWDB')
            
            if market_to_gdp is None or market_to_gdp.empty:
                return None
            
            # Get the most recent value
            latest_value = market_to_gdp.iloc[-1]
            
            self.logger.info(f"Found market cap to GDP ratio: {latest_value:.2f}%")
            print(f"Found market cap to GDP ratio: {latest_value:.2f}%")
            
            return float(latest_value)
        except Exception as e:
            return self._log_error("fetching market to GDP ratio", e)
    
    def get_gdp_metrics(self) -> Dict[str, float]:
        """Get GDP and related metrics"""
        try:
            print(f"\nFetching US GDP metrics")
            
            gdp = self._safe_get_fred_series('GDP')  # Nominal GDP
            gdp_growth = self._safe_get_fred_series('A191RL1Q225SBEA')  # Real GDP Growth Rate
            
            if gdp is None or gdp_growth is None or gdp.empty or gdp_growth.empty:
                return {'gdp': None, 'gdp_growth': None}
            
            # Get the most recent values
            latest_gdp = gdp.iloc[-1]
            latest_gdp_growth = gdp_growth.iloc[-1]
            
            self.logger.info(f"Found GDP: ${latest_gdp/1000:.2f} trillion, Growth Rate: {latest_gdp_growth:.2f}%")
            print(f"Found GDP: ${latest_gdp/1000:.2f} trillion")
            print(f"GDP Growth Rate: {latest_gdp_growth:.2f}%")
            
            return {
                'gdp': float(latest_gdp),
                'gdp_growth': float(latest_gdp_growth)
            }
        except Exception as e:
            return self._log_error("fetching GDP metrics", e)
    
    def get_government_metrics(self) -> Dict[str, float]:
        """Get government debt and deficit metrics"""
        try:
            print(f"\nFetching US government debt and deficit metrics")
            
            govt_debt = self._safe_get_fred_series('GFDEBTN')  # Federal Debt: Total Public Debt
            govt_deficit = self._safe_get_fred_series('FYFSD')  # Federal Surplus or Deficit
            
            if govt_debt is None or govt_deficit is None or govt_debt.empty or govt_deficit.empty:
                return {'govt_debt': None, 'govt_deficit': None, 'debt_to_gdp': None}
            
            # Get the most recent values
            latest_debt = govt_debt.iloc[-1]
            latest_deficit = govt_deficit.iloc[-1]
            
            # Get GDP for debt-to-GDP calculation
            gdp = self._safe_get_fred_series('GDP')
            
            if gdp is None or gdp.empty:
                debt_to_gdp = None
            else:
                latest_gdp = gdp.iloc[-1]
                debt_to_gdp = (latest_debt / latest_gdp) * 100  # Convert to percentage
            
            self.logger.info(f"Found Government Debt: ${latest_debt/1000000:.2f} trillion")
            self.logger.info(f"Found Government Deficit: ${latest_deficit/1000:.2f} billion")
            if debt_to_gdp:
                self.logger.info(f"Calculated Debt-to-GDP: {debt_to_gdp:.2f}%")
            
            print(f"Government Debt: ${latest_debt/1000000:.2f} trillion")
            print(f"Government {'Deficit' if latest_deficit < 0 else 'Surplus'}: ${abs(latest_deficit)/1000:.2f} billion")
            if debt_to_gdp:
                print(f"Debt-to-GDP: {debt_to_gdp:.2f}%")
            
            return {
                'govt_debt': float(latest_debt),
                'govt_deficit': float(latest_deficit),
                'debt_to_gdp': float(debt_to_gdp) if debt_to_gdp is not None else None
            }
        except Exception as e:
            return self._log_error("fetching government metrics", e)
    
    def get_10yr_yield(self) -> float:
        """Get current 10-year Treasury yield"""
        try:
            print(f"\nFetching US 10-year Treasury yield")
            
            treasury_10y = self._safe_get_fred_series('DGS10')
            
            if treasury_10y is None or treasury_10y.empty:
                return None
            
            # Get the most recent value
            latest_yield = treasury_10y.iloc[-1]
            
            self.logger.info(f"Found 10-year Treasury yield: {latest_yield:.2f}%")
            print(f"Found 10-year Treasury yield: {latest_yield:.2f}%")
            
            return float(latest_yield)
        except Exception as e:
            return self._log_error("fetching 10-year Treasury yield", e)
    
    def get_inflation_rate(self) -> float:
        """Get current US inflation rate (CPI year-over-year change)"""
        try:
            print(f"\nFetching US inflation rate")
            
            cpi = self._safe_get_fred_series('CPIAUCSL')
            
            if cpi is None or cpi.empty or len(cpi) < 13:  # Need at least 13 months
                return None
            
            # Calculate year-over-year change
            latest_cpi = cpi.iloc[-1]
            year_ago_cpi = cpi.iloc[-13]  # 12 months ago
            
            inflation_rate = ((latest_cpi / year_ago_cpi) - 1) * 100
            
            self.logger.info(f"Calculated inflation rate: {inflation_rate:.2f}%")
            print(f"Found inflation rate: {inflation_rate:.2f}%")
            
            return float(inflation_rate)
        except Exception as e:
            return self._log_error("calculating inflation rate", e)
    
    def get_asset_prices(self) -> Dict[str, float]:
        """Get various asset prices in a single call"""
        return {
            'gold_price': self.get_asset_price("GC=F", "Gold", "per troy ounce"),
            'bitcoin_price': self.get_asset_price("BTC-USD", "Bitcoin"),
            'wti_crude_price': self.get_asset_price("CL=F", "WTI Crude Oil", "per barrel")
        }
    
    def get_asset_price(self, ticker_symbol: str, asset_name: str, unit: str = "") -> float:
        """Helper method to get asset prices from Yahoo Finance"""
        try:
            # Create ticker object
            ticker = yf.Ticker(ticker_symbol)
            
            # Get current price
            price = ticker.info.get('regularMarketPrice')
            print(f"\nFetching {asset_name} price ({ticker_symbol})")
            
            if price:
                unit_text = f" {unit}" if unit else ""
                print(f"Found {asset_name} price: ${price}{unit_text}")
                return float(price)
            
            print(f"No {asset_name} price data available")
            return None
        except Exception as e:
            return self._log_error(f"fetching {asset_name} price", e)

    def get_gold_price(self) -> float:
        """Get current gold price using GC=F (Gold Futures)"""
        return self.get_asset_price("GC=F", "Gold", "per troy ounce")

    def get_bitcoin_price(self) -> float:
        """Get current Bitcoin price using BTC-USD"""
        return self.get_asset_price("BTC-USD", "Bitcoin")

    def get_wti_crude_price(self) -> float:
        """Get current WTI Crude Oil price using CL=F (Crude Oil Futures)"""
        return self.get_asset_price("CL=F", "WTI Crude Oil", "per barrel")

    def get_equity_risk_premium(self) -> Dict[str, float]:
        """Get equity risk premium (ERP) from Damodaran's data"""
        try:
            # Check if openpyxl is installed
            try:
                importlib.import_module('openpyxl')
            except ImportError:
                self.logger.error("openpyxl dependency is required but not installed")
                print("[bold red]Error: openpyxl dependency is required but not installed.[/bold red]")
                print("Please install it with: pip install openpyxl>=3.0.0")
                # Fall back to calculation immediately if openpyxl is not available
                return self._calculate_equity_risk_premium()
            
            # URL for Damodaran's implied ERP spreadsheet
            url = "https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx"
            self.logger.info(f"Fetching equity risk premium from Damodaran's dataset: {url}")
            print(f"\nFetching equity risk premium from Damodaran's dataset")
            
            if not self._download_file(url, "damodaran_temp.xlsx"):
                return self._calculate_equity_risk_premium()
            
            # Read the Excel file
            df = pd.read_excel("damodaran_temp.xlsx")
            
            # The ERP is in the column 'ERP' or similar
            # Find the column with ERP data (column names may vary)
            erp_column = None
            for col in df.columns:
                if 'ERP' in str(col).upper():
                    erp_column = col
                    break
                
            if not erp_column:
                self.logger.error("Could not find ERP column in Damodaran's data")
                raise Exception("Could not find ERP column in the data")
            
            # Get the most recent non-NaN value
            last_valid_index = df[erp_column].last_valid_index()
            erp_value = df.loc[last_valid_index, erp_column]
            last_date = df.iloc[last_valid_index, 0]  # Assuming first column is date
            
            # Convert to float if it's not already
            try:
                erp_value = float(erp_value)
            except (ValueError, TypeError):
                self.logger.warning(f"Could not convert ERP value '{erp_value}' to float")
                # Try to extract numeric value if it's a string with % or other characters
                if isinstance(erp_value, str):
                    erp_value = erp_value.replace('%', '').strip()
                    try:
                        erp_value = float(erp_value)
                    except (ValueError, TypeError):
                        self.logger.error(f"Failed to extract numeric value from '{erp_value}'")
                        raise Exception(f"Invalid ERP value format: {erp_value}")
            
            # Log the result
            self.logger.info(f"Found equity risk premium: {erp_value}% (as of {last_date})")
            print(f"Found equity risk premium: {erp_value}%")
            
            # Clean up temp file
            if os.path.exists("damodaran_temp.xlsx"):
                os.remove("damodaran_temp.xlsx")
            
            return {
                'value': erp_value,
                'date': str(last_date)
            }
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists("damodaran_temp.xlsx"):
                os.remove("damodaran_temp.xlsx")
            
            return self._log_error("fetching Damodaran's equity risk premium", e)
    
    def _calculate_equity_risk_premium(self) -> Dict[str, float]:
        """Helper method to calculate ERP as fallback"""
        try:
            self.logger.info("Falling back to calculation for equity risk premium")
            print("Falling back to calculation for equity risk premium")
            
            # Get P/E ratio for the market
            pe_ratio = self.get_pe_ratio()
            
            # Calculate earnings yield (inverse of P/E ratio)
            if pe_ratio and pe_ratio > 0:
                earnings_yield = (1 / pe_ratio) * 100  # Convert to percentage
            else:
                self.logger.warning("Could not calculate earnings yield: invalid P/E ratio")
                return {'value': None}
            
            # Get 10-year Treasury yield as risk-free rate
            risk_free_rate = self.get_10yr_yield()
            
            if risk_free_rate is None:
                self.logger.warning("Could not get risk-free rate")
                return {'value': None}
            
            # Calculate equity risk premium
            risk_premium = earnings_yield - risk_free_rate
            
            self.logger.info(f"Calculated equity risk premium: {risk_premium:.2f}% (Earnings Yield: {earnings_yield:.2f}%, Risk-Free Rate: {risk_free_rate:.2f}%)")
            print(f"Calculated equity risk premium: {risk_premium:.2f}%")
            print(f"(Earnings Yield: {earnings_yield:.2f}%, Risk-Free Rate: {risk_free_rate:.2f}%)")
            
            return {
                'value': risk_premium,
                'earnings_yield': earnings_yield,
                'risk_free_rate': risk_free_rate
            }
        except Exception as e:
            return self._log_error("calculating equity risk premium", e)
    
    def get_earnings_growth(self) -> Dict[str, float]:
        """
        Get US stock market earnings growth over the last 12 months
        
        This uses S&P 500 earnings data from FRED (S&P 500 Earnings)
        Series ID: SP500 (S&P 500 Index) and MULTPL provides the earnings data
        """
        try:
            # Get S&P 500 earnings per share data (quarterly)
            self.logger.info("Fetching S&P 500 earnings data from FRED")
            print(f"\nFetching S&P 500 earnings growth data")
            
            # Get quarterly earnings data - using Corporate Profits as a proxy
            corporate_profits = self.fred.get_series('CP')
            
            # Need at least 5 quarters of data to calculate YoY growth
            if len(corporate_profits) < 5:
                self.logger.warning("Not enough earnings data to calculate growth")
                return {'growth_rate': None}
            
            # Get the most recent value and the value from a year ago
            recent_value = corporate_profits.iloc[-1]
            year_ago_value = corporate_profits.iloc[-5]  # Quarterly data, so -5 is a year ago
            
            # Calculate year-over-year growth rate
            if year_ago_value <= 0:
                self.logger.warning("Previous year earnings negative or zero, cannot calculate growth rate")
                return {'growth_rate': None}
            
            growth_rate = ((recent_value / year_ago_value) - 1) * 100
            
            # Get the dates for context
            recent_date = corporate_profits.index[-1]
            year_ago_date = corporate_profits.index[-5]
            
            self.logger.info(f"Calculated corporate profits growth: {growth_rate:.2f}% (comparing {recent_date} vs {year_ago_date})")
            print(f"Found corporate profits growth: {growth_rate:.2f}%")
            
            return {
                'growth_rate': growth_rate,
                'recent_value': float(recent_value),
                'year_ago_value': float(year_ago_value),
                'recent_date': str(recent_date.strftime('%Y-%m-%d')),
                'year_ago_date': str(year_ago_date.strftime('%Y-%m-%d'))
            }
        except Exception as e:
            return self._log_error("calculating earnings growth", e)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all available metrics"""
        # Use the metric definitions to get all metrics
        metrics = {}
        
        for metric_name, (func, _) in self.get_metric_definitions().items():
            if metric_name != 'US All Metrics':  # Avoid recursion
                try:
                    result = func()
                    
                    # Handle different result formats
                    if isinstance(result, dict) and 'value' in result:
                        metrics[self._normalize_metric_name(metric_name)] = result['value']
                    elif isinstance(result, dict):
                        # For metrics that return multiple values (e.g., credit_spreads)
                        for key, value in result.items():
                            metrics[key] = value
                    else:
                        metrics[self._normalize_metric_name(metric_name)] = result
                except Exception as e:
                    self.logger.error(f"Error getting {metric_name}: {str(e)}")
                    metrics[self._normalize_metric_name(metric_name)] = None
        
        return metrics
    
    def _normalize_metric_name(self, metric_name: str) -> str:
        """Convert display metric name to normalized variable name"""
        if metric_name == 'US P/E Ratio':
            return 'pe_ratio'
        elif metric_name == 'US CAPE Ratio':
            return 'cape_ratio'
        elif metric_name == 'US Credit Spreads':
            return 'credit_spreads'
        elif metric_name == 'US Stock Market / GDP':
            return 'market_to_gdp'
        elif metric_name == 'US GDP':
            return 'gdp'
        elif metric_name == 'US Government Debt & Deficit':
            return 'government'
        elif metric_name == 'US 10-Year Yield':
            return '10yr_yield'
        elif metric_name == 'US Inflation Rate':
            return 'inflation_rate'
        elif metric_name == 'US Equity Risk Premium':
            return 'equity_risk_premium'
        elif metric_name == 'US Earnings Growth':
            return 'earnings_growth'
        elif metric_name == 'Gold Price':
            return 'gold_price'
        elif metric_name == 'Bitcoin Price':
            return 'bitcoin_price'
        elif metric_name == 'WTI Crude Oil Price':
            return 'wti_crude_price'
        return metric_name.lower().replace(' ', '_')

    def get_metric_definitions(self) -> Dict[str, tuple]:
        """Return a mapping of metric names to their functions and sources"""
        return {
            'US P/E Ratio': (self.get_pe_ratio, 'Yahoo Finance - VTI (Total US Market)'),
            'US CAPE Ratio': (self.get_cape_ratio, 'Robert Shiller\'s Dataset'),
            'US Credit Spreads': (self.get_credit_spreads, 'FRED - Moody\'s BAA Corporate Bond'),
            'US Stock Market / GDP': (self.get_market_to_gdp, 'FRED - Stock Market Capitalization to GDP'),
            'US GDP': (self.get_gdp_metrics, 'FRED - Bureau of Economic Analysis'),
            'US Government Debt & Deficit': (self.get_government_metrics, 'FRED - Treasury Department'),
            'US 10-Year Yield': (self.get_10yr_yield, 'FRED - Treasury Department'),
            'US Inflation Rate': (self.get_inflation_rate, 'FRED - Bureau of Labor Statistics'),
            'US Equity Risk Premium': (self.get_equity_risk_premium, 'NYU Stern - Aswath Damodaran'),
            'US Earnings Growth': (self.get_earnings_growth, 'FRED - Corporate Profits'),
            'Gold Price': (self.get_gold_price, 'Yahoo Finance - Gold Futures (GC=F)'),
            'Bitcoin Price': (self.get_bitcoin_price, 'Yahoo Finance - BTC-USD'),
            'WTI Crude Oil Price': (self.get_wti_crude_price, 'Yahoo Finance - Crude Oil Futures (CL=F)'),
            'US All Metrics': (self.get_all_metrics, 'Multiple Sources')
        }

    def get_metric_by_name(self, metric_name: str) -> Dict[str, Any]:
        """Get a specific metric by name with timestamp and source"""
        metric_map = self.get_metric_definitions()
        
        func, source = metric_map[metric_name]
        result = func()
        
        # For single metrics, convert to dict with timestamp and source
        if not isinstance(result, dict):
            result = {
                'value': result,
                'timestamp': datetime.now().strftime('%Y-%m-%d'),
                'source': source
            }
        else:
            # For metric dictionaries, add timestamp and source
            result['timestamp'] = self.get_timestamp_for_metric(metric_name)
            result['source'] = source
        
        # Export to CSV if enabled
        if self.csv_export_path:
            self._export_to_csv(metric_name, result.copy())
        
        return result

    def get_timestamp_for_metric(self, metric_name: str) -> str:
        """Get the appropriate timestamp for each metric type"""
        try:
            if metric_name == 'US GDP':
                gdp = self.fred.get_series('GDP')
                return gdp.index[-1].strftime('%Y-%m-%d')
            elif metric_name == 'US Government Debt & Deficit':
                debt = self.fred.get_series('GFDEBTN')
                return debt.index[-1].strftime('%Y-%m-%d')
            elif metric_name == 'US Inflation Rate':
                cpi = self.fred.get_series('CPIAUCSL')
                return cpi.index[-1].strftime('%Y-%m-%d')
            elif metric_name == 'US Credit Spreads':
                baa = self.fred.get_series('BAA')
                return baa.index[-1].strftime('%Y-%m-%d')
            elif metric_name == 'US CAPE Ratio':
                try:
                    # Get date from Shiller's data
                    url = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
                    df = pd.read_excel(url, sheet_name='Data', header=7)
                    # Date is in the 'Date' column, get the last non-NaN CAPE row
                    last_date = df.loc[df['CAPE'].last_valid_index(), 'Date']
                    # Convert to datetime if it's not already
                    if not isinstance(last_date, datetime):
                        # Shiller's dates are often in decimal year format (e.g., 2023.1)
                        year = int(last_date)
                        month = int(round((last_date - year) * 12)) + 1
                        last_date = datetime(year, month, 1)
                    return last_date.strftime('%Y-%m-%d')
                except Exception:
                    # Fallback to FRED if Shiller's data fails
                    cape = self.fred.get_series('CSUSHPINSA')
                    return cape.index[-1].strftime('%Y-%m-%d')
            else:
                return datetime.now().strftime('%Y-%m-%d')
        except Exception:
            return 'Date not available'

    def get_historical_data(self, series_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get historical data for a FRED series
        
        Args:
            series_id: FRED series ID
            start_date: Start date in 'YYYY-MM-DD' format (optional)
            end_date: End date in 'YYYY-MM-DD' format (optional)
            
        Returns:
            DataFrame with historical data
        """
        try:
            # Convert string dates to datetime if provided
            start = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            end = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
            
            # Get data from FRED
            self.logger.info(f"Fetching historical data for series {series_id}")
            data = self.fred.get_series(series_id, observation_start=start, observation_end=end)
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['value'])
            df.index.name = 'date'
            
            return df
        except Exception as e:
            self.logger.error(f"Error fetching historical data for {series_id}: {str(e)}", exc_info=True)
            print(f"[bold red]Error fetching historical data: {str(e)}[/bold red]")
            return pd.DataFrame()

    def _plot_helper(self, save_path: Optional[str] = None) -> bool:
        """Helper function to check for matplotlib and handle plot saving"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            return True
        except ImportError:
            self.logger.error("matplotlib is required for plotting but not installed")
            print("[bold red]Error: matplotlib is required for plotting but not installed.[/bold red]")
            print("Please install it with: pip install matplotlib")
            return False
            
    def _save_and_show_plot(self, plt, save_path: Optional[str] = None):
        """Helper to save and display plots"""
        # Save if requested
        if save_path:
            plt.savefig(save_path)
            print(f"[bold green]Plot saved to {save_path}[/bold green]")
        
        # Show the plot
        plt.show()

    def plot_series(self, series_id: str, title: str, start_date: Optional[str] = None, 
                    end_date: Optional[str] = None, save_path: Optional[str] = None) -> None:
        """
        Plot a FRED series and optionally save to file
        
        Args:
            series_id: FRED series ID
            title: Title for the plot
            start_date: Start date in 'YYYY-MM-DD' format (optional)
            end_date: End date in 'YYYY-MM-DD' format (optional)
            save_path: Path to save the plot (optional)
        """
        try:
            # Check if matplotlib is installed
            if not self._plot_helper():
                return
            
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            # Get the data
            df = self.get_historical_data(series_id, start_date, end_date)
            
            if df.empty:
                print(f"[bold yellow]No data available for series {series_id}[/bold yellow]")
                return
            
            # Get series information
            series_info = self.fred.get_series_info(series_id)
            units = series_info.get('units', '')
            
            # Create the plot
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['value'])
            
            # Format the plot
            plt.title(f"{title} ({series_id})")
            plt.xlabel('Date')
            plt.ylabel(f"Value ({units})" if units else "Value")
            
            # Format x-axis dates
            ax = plt.gca()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # Add grid
            plt.grid(True, alpha=0.3)
            
            # Tight layout
            plt.tight_layout()
            
            self._save_and_show_plot(plt, save_path)
            
        except Exception as e:
            self.logger.error(f"Error plotting series {series_id}: {str(e)}", exc_info=True)
            print(f"[bold red]Error plotting series: {str(e)}[/bold red]")

    def plot_multiple_series(self, series_ids: List[str], labels: List[str], title: str, 
                             start_date: Optional[str] = None, end_date: Optional[str] = None,
                             save_path: Optional[str] = None) -> None:
        """
        Plot multiple FRED series on the same graph
        
        Args:
            series_ids: List of FRED series IDs
            labels: List of labels for each series
            title: Title for the plot
            start_date: Start date in 'YYYY-MM-DD' format (optional)
            end_date: End date in 'YYYY-MM-DD' format (optional)
            save_path: Path to save the plot (optional)
        """
        try:
            # Check if matplotlib is installed
            if not self._plot_helper():
                return
            
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            if len(series_ids) != len(labels):
                raise ValueError("Number of series IDs must match number of labels")
            
            plt.figure(figsize=(12, 6))
            
            # Plot each series
            for i, (series_id, label) in enumerate(zip(series_ids, labels)):
                df = self.get_historical_data(series_id, start_date, end_date)
                
                if not df.empty:
                    plt.plot(df.index, df['value'], label=label)
                else:
                    print(f"[bold yellow]No data available for series {series_id}[/bold yellow]")
            
            # Format the plot
            plt.title(title)
            plt.xlabel('Date')
            plt.ylabel('Value')
            plt.legend()
            
            # Format x-axis dates
            ax = plt.gca()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            
            # Add grid
            plt.grid(True, alpha=0.3)
            
            # Tight layout
            plt.tight_layout()
            
            self._save_and_show_plot(plt, save_path)
            
        except Exception as e:
            self.logger.error(f"Error plotting multiple series: {str(e)}", exc_info=True)
            print(f"[bold red]Error plotting multiple series: {str(e)}[/bold red]")

    def _log_error(self, message: str, exception: Exception):
        """Centralized error logging and display"""
        self.logger.error(f"{message}: {str(exception)}", exc_info=True)
        print(f"Error {message.lower()}: {str(exception)}")
        return None

    def _safe_get_fred_series(self, series_id: str) -> Optional[pd.Series]:
        """Safely fetch a series from FRED with error handling"""
        try:
            return self.fred.get_series(series_id)
        except Exception as e:
            return self._log_error(f"fetching FRED series {series_id}", e)

    def _download_file(self, url: str, temp_filename: str) -> bool:
        """Download file from URL and save temporarily"""
        try:
            self.logger.info(f"Downloading data from: {url}")
            
            start_time = time.time()
            response = requests.get(url)
            self.logger.info(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch data. Status code: {response.status_code}")
                raise Exception(f"Failed to fetch data: HTTP {response.status_code}")
            
            # Save the file temporarily
            with open(temp_filename, "wb") as f:
                f.write(response.content)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Request completed in {elapsed_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            return self._log_error(f"downloading {url}", e)

def display_ascii_art():
    console = Console()
    ascii_art = """
[bold magenta]
    ███╗   ███╗ █████╗ ██████╗ ██╗  ██╗███████╗████████╗███████╗
    ████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝██╔════╝
    ██╔████╔██║███████║██████╔╝█████╔╝ █████╗     ██║   ███████╗
    ██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ ██╔══╝     ██║   ╚════██║
    ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗███████╗   ██║   ███████║
    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝
[/bold magenta]
[bold cyan]    ✨ Financial Analytics ✨ [/bold cyan]
    """
    console.print(Panel(ascii_art, border_style="magenta"))

def get_metric_choices() -> List[str]:
    return [
        '1. US P/E Ratio',
        '2. US CAPE Ratio',
        '3. US Credit Spreads',
        '4. US Stock Market / GDP',
        '5. US GDP',
        '6. US Government Debt & Deficit',
        '7. US 10-Year Yield',
        '8. US Inflation Rate',
        '9. US Equity Risk Premium',
        '10. US Earnings Growth',
        '11. Gold Price',
        '12. Bitcoin Price',
        '13. WTI Crude Oil Price',
        '14. US All Metrics',
        '15. Export All Metrics to CSV',
        '16. Plot Historical Data',
        '17. Plot Multiple Series',
    ]

def display_metric_result(metric_name: str, value: Dict[str, Any]):
    console = Console()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("As of Date", style="yellow")
    table.add_column("Source", style="blue")
    
    timestamp = value.pop('timestamp') if 'timestamp' in value else 'Date not available'
    source = value.pop('source') if 'source' in value else 'Source not available'
    
    # Special handling for equity risk premium which might have a date field
    if 'date' in value and metric_name == 'US Equity Risk Premium':
        date_value = value.pop('date')
        if date_value and timestamp == 'Date not available':
            timestamp = date_value
    
    # Special handling for earnings growth
    if metric_name == 'US Earnings Growth' and 'growth_rate' in value:
        growth_rate = value.pop('growth_rate')
        if growth_rate is None:
            table.add_row(metric_name, "Data unavailable", timestamp, source)
        else:
            table.add_row(metric_name, f"{float(growth_rate):.2f}%", timestamp, source)
        
        # Add additional details if needed
        for k, v in value.items():
            if k not in ['timestamp', 'source', 'date']:
                if v is None:
                    table.add_row(k, "Data unavailable", timestamp, source)
                else:
                    try:
                        formatted_value = f"{float(v):.2f}"
                        if k.endswith('_date'):
                            formatted_value = str(v)
                        table.add_row(k, formatted_value, timestamp, source)
                    except (ValueError, TypeError):
                        table.add_row(k, str(v), timestamp, source)
    elif len(value) == 1 and 'value' in value:
        # Single metric
        if value['value'] is None:
            table.add_row(metric_name, "Data unavailable", timestamp, source)
        else:
            # Try to format as float, but handle string values gracefully
            try:
                formatted_value = f"{float(value['value']):.2f}"
                if metric_name == 'US Equity Risk Premium':
                    formatted_value += '%'
                table.add_row(metric_name, formatted_value, timestamp, source)
            except (ValueError, TypeError):
                # If we can't format as float, just display as is
                table.add_row(metric_name, str(value['value']), timestamp, source)
    else:
        # Multiple metrics
        for k, v in value.items():
            if k not in ['timestamp', 'source', 'date', 'growth_rate']:
                if v is None:
                    table.add_row(k, "Data unavailable", timestamp, source)
                else:
                    try:
                        # Format based on metric type
                        if k == 'govt_debt':
                            # Format in trillions for readability
                            formatted_value = f"${float(v)/1000000:.2f} trillion"
                        elif k == 'govt_deficit':
                            # Format in billions with sign
                            formatted_value = f"${abs(float(v))/1000:.2f} billion {'deficit' if float(v) < 0 else 'surplus'}"
                        elif k == 'gdp':
                            # Format in trillions
                            formatted_value = f"${float(v)/1000:.2f} trillion"
                        elif k == 'debt_to_gdp' or k == 'gdp_growth' or k.endswith('_rate'):
                            # Percentages
                            formatted_value = f"{float(v):.2f}%"
                        elif k == 'baa_spread':
                            # Basis points
                            formatted_value = f"{float(v):.2f}% ({int(float(v)*100)} bps)"
                        else:
                            # Default formatting
                            formatted_value = f"{float(v):.2f}"
                    except (ValueError, TypeError):
                        # If we can't format as float, just display as is
                        formatted_value = str(v)
                    
                    table.add_row(k, formatted_value, timestamp, source)
    
    console.print(Panel(table, title=f"[bold cyan]{metric_name}[/bold cyan]", 
                      border_style="blue"))

def export_all_metrics_to_csv(metrics: USMarketMetrics, csv_path: str) -> None:
    """Export all metrics to a CSV file"""
    console = Console()
    
    with console.status("[bold cyan]Exporting all metrics to CSV...[/bold cyan]", spinner="dots"):
        try:
            # Create a new metrics object with CSV export enabled
            export_metrics = USMarketMetrics(
                fred_api_key=os.getenv('FRED_API_KEY'),
                csv_export_path=csv_path
            )
            
            # Get all metrics using the defined metric list
            metric_names = [name for name in export_metrics.get_metric_definitions().keys() 
                          if name != 'US All Metrics']
            
            for metric_name in metric_names:
                console.print(f"[cyan]Fetching {metric_name}...[/cyan]")
                export_metrics.get_metric_by_name(metric_name)
                
            console.print(f"[bold green]Successfully exported all metrics to {csv_path}[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]Error exporting metrics to CSV: {str(e)}[/bold red]")

def display_menu():
    """Display the menu of available metrics"""
    console = Console()
    
    menu_table = Table(show_header=False, box=None)
    menu_table.add_column("Option", style="cyan")
    menu_table.add_column("Description", style="white")
    
    choices = get_metric_choices()
    for choice in choices:
        number, description = choice.split('. ', 1)
        menu_table.add_row(f"[bold cyan]{number}.[/bold cyan]", description)
    
    # Add the Q option for exit
    menu_table.add_row("[bold cyan]Q.[/bold cyan]", "Exit")
    
    console.print(menu_table)

def get_user_choice() -> str:
    """Get the user's choice from the menu"""
    while True:
        try:
            choice = input("\n: ").strip()
            
            # Check for Q/q to exit
            if choice.lower() == 'q':
                return 'Exit'
                
            choice_num = int(choice)
            
            if 1 <= choice_num <= 18:
                # Convert number to menu text
                choices = get_metric_choices()
                for menu_item in choices:
                    if menu_item.startswith(f"{choice_num}. "):
                        return menu_item.split('. ', 1)[1]
                        
            print("[bold red]Invalid choice. Please enter a number between 1 and 18 or 'q' to exit.[/bold red]")
        except ValueError:
            print("[bold red]Please enter a valid number or 'q' to exit.[/bold red]")

def main():
    # Get FRED API key from environment variable
    fred_api_key = os.getenv('FRED_API_KEY')
    
    if not fred_api_key:
        rprint("[bold red]Error:[/bold red] Please set FRED_API_KEY environment variable")
        return
    
    # Initialize metrics without CSV export initially
    metrics = USMarketMetrics(fred_api_key)
    console = Console()
    csv_path = None

    while True:
        console.clear()
        display_ascii_art()
        display_menu()
        
        # Get user choice
        choice_text = get_user_choice()
        
        if choice_text == 'Exit':
            console.print("\n[bold cyan]Thanks for using Market Metrics Explorer! 👋[/bold cyan]\n")
            break
        elif choice_text == 'Export All Metrics to CSV':
            # Ask for CSV path
            default_path = f"market_metrics_{datetime.now().strftime('%Y%m%d')}.csv"
            print(f"\nEnter the path for the CSV file [default: {default_path}]: ", end="")
            user_path = input().strip()
            csv_path = user_path if user_path else default_path
            
            export_all_metrics_to_csv(metrics, csv_path)
            console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
            input()
            continue
        elif choice_text == 'Plot Historical Data':
            # Ask for series ID
            series_id = questionary.text("Enter FRED series ID (e.g., GDP, CPIAUCSL, DGS10):").ask()
            
            # Ask for date range
            default_start = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
            start_date = questionary.text(f"Enter start date (YYYY-MM-DD) [default: {default_start}]:").ask()
            start_date = start_date if start_date else default_start
            
            end_date = questionary.text("Enter end date (YYYY-MM-DD) [default: today]:").ask()
            end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
            
            # Ask for title
            title = questionary.text(f"Enter plot title [default: {series_id} Historical Data]:").ask()
            title = title if title else f"{series_id} Historical Data"
            
            # Ask if user wants to save the plot
            save_plot = questionary.confirm("Do you want to save the plot?").ask()
            save_path = None
            if save_plot:
                default_save_path = f"{series_id}_{datetime.now().strftime('%Y%m%d')}.png"
                save_path = questionary.text(f"Enter save path [default: {default_save_path}]:").ask()
                save_path = save_path if save_path else default_save_path
            
            # Plot the data
            metrics.plot_series(series_id, title, start_date, end_date, save_path)
            
            console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
            input()
            continue
        elif choice_text == 'Plot Multiple Series':
            # Ask for series IDs
            series_input = questionary.text("Enter FRED series IDs separated by commas (e.g., GDP,CPIAUCSL,DGS10):").ask()
            series_ids = [s.strip() for s in series_input.split(',')]
            
            # Ask for labels
            labels_input = questionary.text("Enter labels for each series separated by commas:").ask()
            labels = [l.strip() for l in labels_input.split(',')]
            
            # Ensure same number of labels as series
            if len(labels) < len(series_ids):
                labels.extend([f"Series {i+1}" for i in range(len(labels), len(series_ids))])
            
            # Ask for date range
            default_start = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
            start_date = questionary.text(f"Enter start date (YYYY-MM-DD) [default: {default_start}]:").ask()
            start_date = start_date if start_date else default_start
            
            end_date = questionary.text("Enter end date (YYYY-MM-DD) [default: today]:").ask()
            end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')
            
            # Ask for title
            title = questionary.text("Enter plot title [default: FRED Data Comparison]:").ask()
            title = title if title else "FRED Data Comparison"
            
            # Ask if user wants to save the plot
            save_plot = questionary.confirm("Do you want to save the plot?").ask()
            save_path = None
            if save_plot:
                default_save_path = f"fred_comparison_{datetime.now().strftime('%Y%m%d')}.png"
                save_path = questionary.text(f"Enter save path [default: {default_save_path}]:").ask()
                save_path = save_path if save_path else default_save_path
            
            # Plot the data
            metrics.plot_multiple_series(series_ids, labels, title, start_date, end_date, save_path)
            
            console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
            input()
            continue
            
        # Show loading spinner
        with console.status("[bold cyan]Fetching data...[/bold cyan]", spinner="dots"):
            try:
                result = metrics.get_metric_by_name(choice_text)
                display_metric_result(choice_text, result)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
        
        # Use console.print instead of input for the prompt
        console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
        input()

if __name__ == "__main__":
    main()
