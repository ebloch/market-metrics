#!/usr/bin/env python
"""Tests for market-metrics modules."""
import sys

def test_constants():
    """Test constants module."""
    from constants import METRIC_GROUPS
    assert 'Valuations' in METRIC_GROUPS
    assert 'US Economy' in METRIC_GROUPS
    assert 'Rates & Credit' in METRIC_GROUPS
    assert 'Assets' in METRIC_GROUPS
    assert isinstance(METRIC_GROUPS['Valuations'], list)
    assert 'World Stock Market P/E Ratios' in METRIC_GROUPS['Valuations']
    print("  constants tests passed")

def test_data_dummy():
    """Test data module with dummy data."""
    from data import get_dummy_data
    dummy = get_dummy_data()
    assert 'US GDP' in dummy
    assert 'World Stock Market P/E Ratios' in dummy
    assert dummy['US GDP']['status'] == 'success'
    assert 'data' in dummy['US GDP']
    print("  data (dummy) tests passed")

def test_data_class_exists():
    """Test that USMarketMetrics class exists in data module."""
    from data import USMarketMetrics
    assert USMarketMetrics is not None
    print("  data class tests passed")

def test_data_fetch_function_exists():
    """Test that fetch_all_metrics_with_progress exists."""
    from data import fetch_all_metrics_with_progress
    assert callable(fetch_all_metrics_with_progress)
    print("  data fetch function tests passed")

def test_display_formatting():
    """Test display formatting functions."""
    from display import format_metric_value
    from data import get_dummy_data
    dummy = get_dummy_data()

    # Test GDP formatting
    gdp_value = format_metric_value('US GDP', dummy['US GDP'])
    assert '$' in gdp_value or 'T' in gdp_value or gdp_value == 'N/A'

    # Test P/E formatting
    pe_value = format_metric_value('World Stock Market P/E Ratios', dummy['World Stock Market P/E Ratios'])
    assert pe_value != ''
    print("  display formatting tests passed")

def test_display_functions_exist():
    """Test that key display functions exist."""
    from display import (
        display_dashboard,
        get_dashboard_choice,
        create_section_panel,
        display_sources,
        format_row_with_dots
    )
    assert callable(display_dashboard)
    assert callable(get_dashboard_choice)
    assert callable(create_section_panel)
    assert callable(display_sources)
    assert callable(format_row_with_dots)
    print("  display function existence tests passed")

def test_display_helper_functions():
    """Test display helper extraction functions."""
    from display import get_japan_pe_from_data, get_gdp_growth_from_data, get_deficit_from_data
    from data import get_dummy_data
    dummy = get_dummy_data()

    # Test Japan P/E extraction
    japan_pe = get_japan_pe_from_data(dummy.get('World Stock Market P/E Ratios'))
    assert japan_pe != ''

    # Test GDP growth extraction
    gdp_growth = get_gdp_growth_from_data(dummy.get('US GDP'))
    assert gdp_growth != ''

    # Test deficit extraction
    deficit = get_deficit_from_data(dummy.get('US Government Debt & Deficit'))
    assert deficit != ''
    print("  display helper function tests passed")

def test_cli_imports():
    """Test that main entry point imports work."""
    # This tests the import structure is correct
    from data import USMarketMetrics, fetch_all_metrics_with_progress, get_dummy_data
    from display import display_dashboard, get_dashboard_choice
    from constants import METRIC_GROUPS
    print("  CLI import tests passed")

def run_all_tests():
    """Run all tests."""
    print("\nRunning tests...\n")
    tests = [
        test_constants,
        test_data_dummy,
        test_data_class_exists,
        test_data_fetch_function_exists,
        test_display_formatting,
        test_display_functions_exist,
        test_display_helper_functions,
        test_cli_imports
    ]
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  {test.__name__} FAILED: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
