#!/usr/bin/env python
"""
Market Metrics Dashboard - Entry Point

A Bloomberg-style market metrics dashboard with real-time financial data.
"""
import argparse
import os
import sys
import logging
from datetime import datetime

from rich import print as rprint
from rich.console import Console

from constants import METRIC_GROUPS
from data import USMarketMetrics, fetch_all_metrics_with_progress, get_dummy_data
from display import (
    display_dashboard,
    get_dashboard_choice,
    display_sources,
    handle_csv_export,
    handle_plot_single,
    handle_plot_multiple
)


def export_for_cron(csv_path: str) -> int:
    """
    Export all metrics to CSV in non-interactive mode (for cron jobs).

    Args:
        csv_path: Path to the CSV file to write/append to

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    # Setup logging for cron (logs to file, not console)
    logger = logging.getLogger('market_metrics_cron')
    logger.setLevel(logging.INFO)

    # Add file handler if not already present
    if not logger.handlers:
        log_file = os.path.join(os.path.dirname(os.path.abspath(csv_path)), 'market_metrics_cron.log')
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
        except Exception:
            # Fall back to current directory if we can't write to csv_path directory
            file_handler = logging.FileHandler('market_metrics_cron.log')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)

    logger.info(f"Starting cron export to {csv_path}")

    # Validate CSV path
    try:
        csv_dir = os.path.dirname(os.path.abspath(csv_path))
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
            logger.info(f"Created directory: {csv_dir}")
    except OSError as e:
        logger.error(f"Cannot create directory for CSV file: {e}")
        print(f"Error: Cannot create directory for CSV file: {e}", file=sys.stderr)
        return 1

    # Check FRED API key
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        logger.error("FRED_API_KEY environment variable not set")
        print("Error: FRED_API_KEY environment variable not set", file=sys.stderr)
        return 1

    try:
        # Create metrics object with CSV export enabled
        export_metrics = USMarketMetrics(
            fred_api_key=fred_api_key,
            csv_export_path=csv_path
        )

        # Get all metric names
        metric_names = [name for name in export_metrics.get_metric_definitions().keys()
                       if name != 'US All Metrics']

        successful_exports = 0
        failed_exports = 0

        for metric_name in metric_names:
            try:
                logger.info(f"Fetching {metric_name}...")
                export_metrics.get_metric_by_name(metric_name)
                successful_exports += 1
            except Exception as e:
                logger.warning(f"Failed to fetch {metric_name}: {e}")
                failed_exports += 1
                # Continue with other metrics even if one fails

        logger.info(f"Export complete: {successful_exports} succeeded, {failed_exports} failed")

        if failed_exports > 0:
            print(f"Warning: {failed_exports} metrics failed to export. Check log for details.", file=sys.stderr)

        if successful_exports == 0:
            logger.error("All metrics failed to export")
            print("Error: All metrics failed to export", file=sys.stderr)
            return 1

        logger.info(f"Successfully exported {successful_exports} metrics to {csv_path}")
        print(f"Successfully exported {successful_exports} metrics to {csv_path}")
        return 0

    except Exception as e:
        logger.error(f"Fatal error during export: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """
    Main entry point for the Market Metrics Dashboard.

    Dashboard-first design: fetches all metrics upfront and displays
    them in a Bloomberg-style grouped layout.

    Use --test flag to run with dummy data for UI testing.
    """
    # Parse command line arguments
    help_epilog = """
examples:
  python market-metrics.py                  Launch interactive dashboard
  python market-metrics.py --export data.csv   Export metrics to CSV and exit
  python market-metrics.py --test           Run with dummy data for UI testing

environment:
  FRED_API_KEY    Required. Get a free key at:
                  https://fred.stlouisfed.org/docs/api/api_key.html

dashboard keys:
  1   Export all metrics to CSV file
  2   Plot a single FRED data series
  3   Plot multiple FRED series for comparison
  S   View data sources and timestamps
  R   Refresh all market data
  Q   Quit the application

metrics:
  Economy:      GDP, GDP Growth, Debt/GDP, Deficit, Inflation, Earnings Growth
  Valuations:   US P/E, Japan P/E, CAPE Ratio, Equity Risk Premium, Buffett Indicator
  Rates:        10-Year Treasury Yield, BAA Credit Spread
  Assets:       Gold, Bitcoin, WTI Crude Oil

data sources:
  FRED API        GDP, Inflation, Treasury Yields, Credit Spreads, Debt/Deficit
  Yahoo Finance   P/E Ratios, Gold, Bitcoin, Oil prices, Market Cap
  Robert Shiller  CAPE Ratio (Cyclically Adjusted P/E)
  NYU Stern       Equity Risk Premium

exit codes (--export mode):
  0   Success - all or some metrics exported
  1   Failure - missing API key, invalid path, or all exports failed
"""
    parser = argparse.ArgumentParser(
        description='Bloomberg-style market metrics dashboard with real-time financial data.',
        epilog=help_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--test', action='store_true',
                        help='run with dummy data for UI testing')
    parser.add_argument('--export', type=str, metavar='PATH',
                        help='export all metrics to CSV file and exit (non-interactive)')
    args = parser.parse_args()

    # Handle --export mode (non-interactive, for cron/scripts)
    if args.export:
        exit_code = export_for_cron(args.export)
        sys.exit(exit_code)

    console = Console()
    metrics = None

    if args.test:
        # Use dummy data for testing
        console.print("[yellow]Running in test mode with dummy data[/yellow]\n")
        all_data = get_dummy_data()
        fetch_timestamp = datetime.now()
    else:
        # Get FRED API key from environment variable
        fred_api_key = os.getenv('FRED_API_KEY')

        if not fred_api_key:
            rprint("[bold red]Error:[/bold red] Please set FRED_API_KEY environment variable")
            return

        # Initialize metrics
        metrics = USMarketMetrics(fred_api_key)

        # Fetch all data upfront with progress indicator
        all_data, fetch_timestamp = fetch_all_metrics_with_progress(metrics)

    # Main loop - display dashboard and handle actions
    while True:
        display_dashboard(all_data, fetch_timestamp)
        choice = get_dashboard_choice()

        if choice == 'exit':
            console.print("\n[bold cyan]Thanks for using Market Metrics Dashboard![/bold cyan]\n")
            break
        elif choice == 'refresh':
            if args.test:
                all_data = get_dummy_data()
                fetch_timestamp = datetime.now()
            else:
                all_data, fetch_timestamp = fetch_all_metrics_with_progress(metrics)
        elif choice == 'export':
            if args.test:
                console.print("[yellow]Export not available in test mode[/yellow]")
                input("Press Enter to continue...")
            else:
                handle_csv_export(metrics, console)
        elif choice == 'plot_single':
            if args.test:
                console.print("[yellow]Plot not available in test mode[/yellow]")
                input("Press Enter to continue...")
            else:
                handle_plot_single(metrics, console)
        elif choice == 'plot_multiple':
            if args.test:
                console.print("[yellow]Multi-plot not available in test mode[/yellow]")
                input("Press Enter to continue...")
            else:
                handle_plot_multiple(metrics, console)
        elif choice == 'sources':
            display_sources(all_data, fetch_timestamp)


if __name__ == "__main__":
    main()
