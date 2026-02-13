"""Display and UI module for market-metrics.

Contains all display functions, formatting helpers, and user interaction handlers.
"""
from datetime import datetime, timedelta
import os
from typing import Dict, Any
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import questionary


def display_ascii_art():
    """Display the ASCII art header."""
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


def display_metric_result(metric_name: str, value: Dict[str, Any]):
    """Display a single metric result in a formatted table."""
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

    # Special handling for World P/E Ratios
    if metric_name == 'World Stock Market P/E Ratios':
        for market_id, market_data in value.items():
            market_name = market_id.upper()
            if market_id == 'us':
                market_name = 'United States'
            elif market_id == 'japan':
                market_name = 'Japan'

            # Extract value and source from market data
            if isinstance(market_data, dict):
                pe_value = market_data.get('value')
                market_source = market_data.get('source', source)
            else:
                pe_value = market_data
                market_source = source

            if pe_value is None:
                table.add_row(f"{market_name}", "Data unavailable", timestamp, market_source)
            else:
                table.add_row(f"{market_name}", f"{float(pe_value):.2f}", timestamp, market_source)
        console.print(Panel(table, title=f"[bold cyan]{metric_name}[/bold cyan]", border_style="blue"))
        return

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
                        elif k == 'gdp' or k == 'market_cap':
                            # Format in trillions
                            formatted_value = f"${float(v)/1000:.2f} trillion"
                        elif k == 'debt_to_gdp' or k == 'gdp_growth' or k == 'ratio_pct' or k.endswith('_rate'):
                            # Percentages
                            formatted_value = f"{float(v):.2f}%"
                        elif k == 'ratio':
                            # Ratio as decimal
                            formatted_value = f"{float(v):.2f}"
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


def format_metric_value(metric_name: str, data: Dict[str, Any]) -> str:
    """
    Format a metric value for dashboard display.

    Returns a formatted string suitable for the dashboard.
    """
    if data is None or data.get('status') == 'error':
        return "N/A"

    result = data.get('data')
    if result is None:
        return "N/A"

    try:
        if metric_name == 'World Stock Market P/E Ratios':
            if isinstance(result, dict):
                us_pe = result.get('us', {})
                if isinstance(us_pe, dict):
                    val = us_pe.get('value')
                else:
                    val = us_pe
                return f"{float(val):.2f}" if val else "N/A"
            return "N/A"

        elif metric_name == 'US CAPE Ratio':
            if isinstance(result, (int, float)):
                return f"{float(result):.2f}"
            elif isinstance(result, dict) and 'value' in result:
                return f"{float(result['value']):.2f}"
            return "N/A"

        elif metric_name == 'US Equity Risk Premium':
            if isinstance(result, dict) and 'value' in result:
                val = result['value']
                return f"{float(val):.2f}%" if val else "N/A"
            return "N/A"

        elif metric_name == 'US Credit Spreads':
            if isinstance(result, dict) and 'baa_spread' in result:
                val = result['baa_spread']
                return f"{int(float(val)*100)} bps" if val else "N/A"
            return "N/A"

        elif metric_name == 'US 10-Year Yield':
            if isinstance(result, (int, float)):
                return f"{float(result):.2f}%"
            elif isinstance(result, dict) and 'value' in result:
                return f"{float(result['value']):.2f}%"
            return "N/A"

        elif metric_name == 'US Stock Market / GDP':
            if isinstance(result, dict) and 'ratio_pct' in result:
                val = result['ratio_pct']
                return f"{float(val):.1f}%" if val else "N/A"
            return "N/A"

        elif metric_name == 'US GDP':
            if isinstance(result, dict) and 'gdp' in result:
                val = result['gdp']
                return f"${float(val)/1000:.1f}T" if val else "N/A"
            return "N/A"

        elif metric_name == 'US Government Debt & Deficit':
            if isinstance(result, dict):
                if 'debt_to_gdp' in result and result['debt_to_gdp']:
                    return f"{float(result['debt_to_gdp']):.1f}%"
            return "N/A"

        elif metric_name == 'US Inflation Rate':
            if isinstance(result, (int, float)):
                return f"{float(result):.1f}%"
            elif isinstance(result, dict) and 'value' in result:
                return f"{float(result['value']):.1f}%"
            return "N/A"

        elif metric_name == 'US Earnings Growth':
            if isinstance(result, dict) and 'growth_rate' in result:
                val = result['growth_rate']
                return f"{float(val):.1f}%" if val else "N/A"
            return "N/A"

        elif metric_name in ['Gold Price', 'Bitcoin Price', 'WTI Crude Oil Price']:
            val = None
            if isinstance(result, (int, float)):
                val = result
            elif isinstance(result, dict) and 'value' in result:
                val = result['value']
            if val is not None:
                if metric_name == 'Bitcoin Price':
                    return f"${float(val):,.0f}"
                else:
                    return f"${float(val):,.2f}"
            return "N/A"

        return str(result)
    except (ValueError, TypeError, KeyError):
        return "N/A"


def get_japan_pe_from_data(data: Dict[str, Any]) -> str:
    """Extract Japan P/E from world PE ratios data."""
    if data is None or data.get('status') == 'error':
        return "N/A"

    result = data.get('data')
    if result is None:
        return "N/A"

    try:
        japan_pe = result.get('japan', {})
        if isinstance(japan_pe, dict):
            val = japan_pe.get('value')
        else:
            val = japan_pe
        return f"{float(val):.2f}" if val else "N/A"
    except (ValueError, TypeError, KeyError):
        return "N/A"


def get_gdp_growth_from_data(data: Dict[str, Any]) -> str:
    """Extract GDP growth from GDP metrics data."""
    if data is None or data.get('status') == 'error':
        return "N/A"

    result = data.get('data')
    if result is None:
        return "N/A"

    try:
        if isinstance(result, dict) and 'gdp_growth' in result:
            val = result['gdp_growth']
            return f"{float(val):.1f}%" if val else "N/A"
    except (ValueError, TypeError, KeyError):
        pass
    return "N/A"


def get_deficit_from_data(data: Dict[str, Any]) -> str:
    """Extract deficit from government metrics data."""
    if data is None or data.get('status') == 'error':
        return "N/A"

    result = data.get('data')
    if result is None:
        return "N/A"

    try:
        if isinstance(result, dict) and 'govt_deficit' in result:
            val = result['govt_deficit']
            if val:
                # Convert from millions to trillions for display
                val_t = abs(float(val)) / 1000000
                sign = "-" if float(val) < 0 else ""
                return f"{sign}${val_t:.1f}T"
    except (ValueError, TypeError, KeyError):
        pass
    return "N/A"


def format_row_with_dots(label: str, value: str, width: int = 24) -> str:
    """Format a row with dot leaders between label and value."""
    dots_space = width - len(label) - len(value)
    if dots_space < 2:
        dots_space = 2
    dots = "." * dots_space
    return f"{label}[dim]{dots}[/dim][green]{value}[/green]"


def create_section_panel(section_name: str, all_data: Dict[str, Any], panel_width: int = 22) -> Panel:
    """
    Create a Rich Panel for a dashboard section with dot leaders.
    """
    # Content width is panel_width minus border (2) and padding (2)
    content_width = panel_width - 4
    rows = []

    if section_name == 'Valuations':
        us_pe = format_metric_value('World Stock Market P/E Ratios', all_data.get('World Stock Market P/E Ratios'))
        japan_pe = get_japan_pe_from_data(all_data.get('World Stock Market P/E Ratios'))
        cape = format_metric_value('US CAPE Ratio', all_data.get('US CAPE Ratio'))
        erp = format_metric_value('US Equity Risk Premium', all_data.get('US Equity Risk Premium'))
        buffett = format_metric_value('US Stock Market / GDP', all_data.get('US Stock Market / GDP'))

        rows = [
            format_row_with_dots("US P/E", us_pe, content_width),
            format_row_with_dots("Japan P/E", japan_pe, content_width),
            format_row_with_dots("US CAPE", cape, content_width),
            format_row_with_dots("US Risk Prem", erp, content_width),
            format_row_with_dots("US Buffett", buffett, content_width),
        ]

    elif section_name == 'Rates & Credit':
        yield_10y = format_metric_value('US 10-Year Yield', all_data.get('US 10-Year Yield'))
        spread = format_metric_value('US Credit Spreads', all_data.get('US Credit Spreads'))

        rows = [
            format_row_with_dots("US10YR", yield_10y, content_width),
            format_row_with_dots("BAA Spread", spread, content_width),
        ]

    elif section_name == 'US Economy':
        gdp = format_metric_value('US GDP', all_data.get('US GDP'))
        gdp_growth = get_gdp_growth_from_data(all_data.get('US GDP'))
        debt_gdp = format_metric_value('US Government Debt & Deficit', all_data.get('US Government Debt & Deficit'))
        deficit = get_deficit_from_data(all_data.get('US Government Debt & Deficit'))
        inflation = format_metric_value('US Inflation Rate', all_data.get('US Inflation Rate'))
        earnings = format_metric_value('US Earnings Growth', all_data.get('US Earnings Growth'))

        rows = [
            format_row_with_dots("GDP", gdp, content_width),
            format_row_with_dots("GDP Growth", gdp_growth, content_width),
            format_row_with_dots("Debt/GDP", debt_gdp, content_width),
            format_row_with_dots("Deficit", deficit, content_width),
            format_row_with_dots("Inflation", inflation, content_width),
            format_row_with_dots("Earnings Growth LTM", earnings, content_width),
        ]

    elif section_name == 'Assets':
        gold = format_metric_value('Gold Price', all_data.get('Gold Price'))
        btc = format_metric_value('Bitcoin Price', all_data.get('Bitcoin Price'))
        oil = format_metric_value('WTI Crude Oil Price', all_data.get('WTI Crude Oil Price'))

        rows = [
            format_row_with_dots("Gold", gold, content_width),
            format_row_with_dots("Bitcoin", btc, content_width),
            format_row_with_dots("WTI", oil, content_width),
        ]

    content = "\n".join(rows)
    return Panel(content, title=f"[bold white]{section_name}[/bold white]", border_style="blue", width=panel_width)


def display_dashboard(all_data: Dict[str, Any], fetch_timestamp: datetime) -> None:
    """
    Display the Bloomberg-style dashboard with all metrics.
    Responsive layout adapts to terminal width.
    """
    console = Console()
    console.clear()

    term_width = console.size.width

    # Header - use smaller version for narrow terminals
    if term_width >= 80:
        header_text = """[bold magenta]
  ███╗   ███╗ █████╗ ██████╗ ██╗  ██╗███████╗████████╗███████╗
  ████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝██╔════╝
  ██╔████╔██║███████║██████╔╝█████╔╝ █████╗     ██║   ███████╗
  ██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ ██╔══╝     ██║   ╚════██║
  ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗███████╗   ██║   ███████║
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝
[/bold magenta]"""
        console.print(header_text)

    console.print("  [bold cyan]MARKET METRICS DASHBOARD[/bold cyan]")
    console.print(f"  [dim]As of: {fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    console.print()

    # Calculate panel width based on terminal width
    if term_width >= 90:
        # Wide: 2x2 grid layout
        panel_width = (term_width - 4) // 2

        valuations_panel = create_section_panel('Valuations', all_data, panel_width)
        rates_panel = create_section_panel('Rates & Credit', all_data, panel_width)
        economy_panel = create_section_panel('US Economy', all_data, panel_width)
        assets_panel = create_section_panel('Assets', all_data, panel_width)

        # Use a grid table for proper alignment
        grid = Table(box=None, show_header=False, padding=(0, 1), expand=False)
        grid.add_column()
        grid.add_column()

        grid.add_row(economy_panel, rates_panel)
        grid.add_row(valuations_panel, assets_panel)

        console.print(grid)

    elif term_width >= 60:
        # Medium: 2-column layout
        panel_width = (term_width - 2) // 2

        valuations_panel = create_section_panel('Valuations', all_data, panel_width)
        rates_panel = create_section_panel('Rates & Credit', all_data, panel_width)
        economy_panel = create_section_panel('US Economy', all_data, panel_width)
        assets_panel = create_section_panel('Assets', all_data, panel_width)

        grid = Table(box=None, show_header=False, padding=(0, 1), expand=False)
        grid.add_column()
        grid.add_column()

        grid.add_row(economy_panel, rates_panel)
        grid.add_row(valuations_panel, assets_panel)

        console.print(grid)

    else:
        # Narrow: 1-column layout
        panel_width = term_width - 4

        console.print(create_section_panel('US Economy', all_data, panel_width))
        console.print(create_section_panel('Valuations', all_data, panel_width))
        console.print(create_section_panel('Rates & Credit', all_data, panel_width))
        console.print(create_section_panel('Assets', all_data, panel_width))

    # Menu bar
    if term_width >= 85:
        menu_text = "[bold cyan][1][/bold cyan] Export CSV  [bold cyan][2][/bold cyan] Plot  [bold cyan][3][/bold cyan] Multi-Plot  [bold cyan][S][/bold cyan] Sources  [bold cyan][R][/bold cyan] Refresh  [bold cyan][Q][/bold cyan] Quit"
    elif term_width >= 70:
        menu_text = "[cyan][1][/cyan]CSV [cyan][2][/cyan]Plot [cyan][3][/cyan]Multi [cyan][S][/cyan]Sources [cyan][R][/cyan]Refresh [cyan][Q][/cyan]Quit"
    else:
        menu_text = "[cyan][1][/cyan]CSV [cyan][2][/cyan]Plot [cyan][S][/cyan]Src [cyan][R][/cyan]Ref [cyan][Q][/cyan]Quit"
    console.print(Panel(menu_text, border_style="magenta"))


def display_sources(all_data: Dict[str, Any], fetch_timestamp: datetime) -> None:
    """Display all metrics with their values, dates, and sources."""
    console = Console()
    console.clear()

    console.print("[bold cyan]DATA SOURCES[/bold cyan]")
    console.print(f"[dim]Fetched: {fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Metric", style="white")
    table.add_column("Value", style="green", justify="right")
    table.add_column("As Of", style="yellow")
    table.add_column("Source", style="dim")

    # Define metrics to display with their display names
    metrics_info = [
        ('US GDP', 'GDP'),
        ('US GDP', 'GDP Growth'),
        ('US Government Debt & Deficit', 'Debt/GDP'),
        ('US Government Debt & Deficit', 'Deficit'),
        ('US Inflation Rate', 'Inflation'),
        ('US Earnings Growth', 'Earnings Growth LTM'),
        ('World Stock Market P/E Ratios', 'US P/E'),
        ('World Stock Market P/E Ratios', 'Japan P/E'),
        ('US CAPE Ratio', 'US CAPE'),
        ('US Equity Risk Premium', 'US Risk Prem'),
        ('US Stock Market / GDP', 'US Buffett'),
        ('US 10-Year Yield', 'US10YR'),
        ('US Credit Spreads', 'BAA Spread'),
        ('Gold Price', 'Gold'),
        ('Bitcoin Price', 'Bitcoin'),
        ('WTI Crude Oil Price', 'WTI'),
    ]

    for metric_key, display_name in metrics_info:
        metric_data = all_data.get(metric_key, {})
        source = metric_data.get('source', 'N/A') if metric_data else 'N/A'

        # Get timestamp from the data
        data_inner = metric_data.get('data', {}) if metric_data else {}
        timestamp = 'N/A'
        if isinstance(data_inner, dict):
            timestamp = data_inner.get('timestamp', 'N/A')
        # For Yahoo Finance metrics, use today's date
        if timestamp == 'N/A' and source and 'Yahoo' in source:
            timestamp = datetime.now().strftime('%Y-%m-%d')

        # Get value based on display name
        if display_name == 'GDP':
            value = format_metric_value('US GDP', metric_data)
        elif display_name == 'GDP Growth':
            value = get_gdp_growth_from_data(metric_data)
        elif display_name == 'Debt/GDP':
            value = format_metric_value('US Government Debt & Deficit', metric_data)
        elif display_name == 'Deficit':
            value = get_deficit_from_data(metric_data)
        elif display_name == 'US P/E':
            value = format_metric_value('World Stock Market P/E Ratios', metric_data)
        elif display_name == 'Japan P/E':
            value = get_japan_pe_from_data(metric_data)
        else:
            value = format_metric_value(metric_key, metric_data)

        table.add_row(display_name, value, timestamp, source)

    console.print(table)
    console.print("\n[cyan]Press Enter to return to dashboard...[/cyan]", end="")
    input()


def get_dashboard_choice() -> str:
    """
    Get user choice from the dashboard menu.

    Returns one of: 'export', 'plot_single', 'plot_multiple', 'sources', 'refresh', 'exit'
    """
    console = Console()
    console.print("\n[cyan]Enter choice:[/cyan] ", end="")

    choice = input().strip().lower()

    if choice == '1':
        return 'export'
    elif choice == '2':
        return 'plot_single'
    elif choice == '3':
        return 'plot_multiple'
    elif choice == 's':
        return 'sources'
    elif choice == 'r':
        return 'refresh'
    elif choice == 'q':
        return 'exit'
    else:
        console.print("[yellow]Invalid choice. Please enter 1, 2, 3, S, R, or Q.[/yellow]")
        return get_dashboard_choice()


def export_all_metrics_to_csv(metrics, csv_path: str) -> None:
    """Export all metrics to a CSV file (interactive mode)"""
    from data import USMarketMetrics
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


def handle_plot_single(metrics, console: Console) -> None:
    """Handle single series plotting."""
    series_id = questionary.text("Enter FRED series ID (e.g., GDP, CPIAUCSL, DGS10):").ask()
    if not series_id:
        return

    default_start = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    start_date = questionary.text(f"Enter start date (YYYY-MM-DD) [default: {default_start}]:").ask()
    start_date = start_date if start_date else default_start

    end_date = questionary.text("Enter end date (YYYY-MM-DD) [default: today]:").ask()
    end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')

    title = questionary.text(f"Enter plot title [default: {series_id} Historical Data]:").ask()
    title = title if title else f"{series_id} Historical Data"

    save_plot = questionary.confirm("Do you want to save the plot?").ask()
    save_path = None
    if save_plot:
        default_save_path = f"{series_id}_{datetime.now().strftime('%Y%m%d')}.png"
        save_path = questionary.text(f"Enter save path [default: {default_save_path}]:").ask()
        save_path = save_path if save_path else default_save_path

    metrics.plot_series(series_id, title, start_date, end_date, save_path)

    console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
    input()


def handle_plot_multiple(metrics, console: Console) -> None:
    """Handle multiple series plotting."""
    series_input = questionary.text("Enter FRED series IDs separated by commas (e.g., GDP,CPIAUCSL,DGS10):").ask()
    if not series_input:
        return
    series_ids = [s.strip() for s in series_input.split(',')]

    labels_input = questionary.text("Enter labels for each series separated by commas:").ask()
    labels = [l.strip() for l in labels_input.split(',')] if labels_input else []

    if len(labels) < len(series_ids):
        labels.extend([f"Series {i+1}" for i in range(len(labels), len(series_ids))])

    default_start = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    start_date = questionary.text(f"Enter start date (YYYY-MM-DD) [default: {default_start}]:").ask()
    start_date = start_date if start_date else default_start

    end_date = questionary.text("Enter end date (YYYY-MM-DD) [default: today]:").ask()
    end_date = end_date if end_date else datetime.now().strftime('%Y-%m-%d')

    title = questionary.text("Enter plot title [default: FRED Data Comparison]:").ask()
    title = title if title else "FRED Data Comparison"

    save_plot = questionary.confirm("Do you want to save the plot?").ask()
    save_path = None
    if save_plot:
        default_save_path = f"fred_comparison_{datetime.now().strftime('%Y%m%d')}.png"
        save_path = questionary.text(f"Enter save path [default: {default_save_path}]:").ask()
        save_path = save_path if save_path else default_save_path

    metrics.plot_multiple_series(series_ids, labels, title, start_date, end_date, save_path)

    console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
    input()


def handle_csv_export(metrics, console: Console) -> None:
    """Handle CSV export."""
    default_path = f"market_metrics_{datetime.now().strftime('%Y%m%d')}.csv"
    print(f"\nEnter the path for the CSV file [default: {default_path}]: ", end="")
    user_path = input().strip()
    csv_path = user_path if user_path else default_path

    export_all_metrics_to_csv(metrics, csv_path)

    console.print("\n[cyan]Press Enter to continue...[/cyan]", end="")
    input()
