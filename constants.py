"""Constants and configuration for market-metrics."""

# Metric groupings for Bloomberg-style dashboard layout
METRIC_GROUPS = {
    'Valuations': ['World Stock Market P/E Ratios', 'US CAPE Ratio', 'US Equity Risk Premium', 'US Stock Market / GDP'],
    'Rates & Credit': ['US Credit Spreads', 'US 10-Year Yield'],
    'US Economy': ['US GDP', 'US Government Debt & Deficit', 'US Inflation Rate', 'US Earnings Growth'],
    'Assets': ['Gold Price', 'Bitcoin Price', 'WTI Crude Oil Price']
}
