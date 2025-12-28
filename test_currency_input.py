"""
Test script for flexible currency input parsing.
Tests keywords: [ALL], [MAJOR], [AFRICAN], comma-separated, etc.
"""

import sys
import os
import importlib.util

# Direct imports to avoid Streamlit dependency
api_client_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logic', 'api_client.py')
spec = importlib.util.spec_from_file_location("api_client", api_client_path)
api_client_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_client_mod)

data_processor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logic', 'data_processor.py')
spec2 = importlib.util.spec_from_file_location("data_processor", data_processor_path)
data_processor_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(data_processor_mod)

TwelveDataClient = api_client_mod.TwelveDataClient
DataProcessor = data_processor_mod.DataProcessor

API_KEY = "b503c569bce848d5b3f4f2f41d29b5d3"


def test_parse_targets():
    """Test the parse_targets function with various inputs."""
    print("=== Testing parse_targets() ===\n")
    
    client = TwelveDataClient(API_KEY)
    
    test_cases = [
        ("", "Empty input"),
        ("   ", "Whitespace only"),
        ("USD, EUR, GBP", "Comma-separated"),
        ("usd,eur,gbp", "Lowercase, no spaces"),
        ("  USD , EUR , GBP  ", "With extra whitespace"),
        ("[DEFAULT]", "Default keyword"),
        ("[MAJOR]", "Major keyword"),
        ("[AFRICAN]", "African keyword"),
        ("MAJOR", "Major without brackets"),
        # ("[ALL]", "All keyword"),  # Skip for now - makes API call
    ]
    
    for input_str, description in test_cases:
        result = DataProcessor.parse_targets(input_str, "ZAR", client)
        print(f"{description}:")
        print(f"  Input: '{input_str}'")
        print(f"  Output: {result}")
        print()


def test_all_keyword():
    """Test [ALL] keyword which makes an API call."""
    print("=== Testing [ALL] keyword (API call) ===\n")
    
    client = TwelveDataClient(API_KEY)
    result = DataProcessor.parse_targets("[ALL]", "ZAR", client)
    
    print(f"[ALL] for ZAR returned {len(result)} currencies:")
    print(f"  {result[:10]}... (showing first 10)")
    print()


def test_generate_pairs_config():
    """Test pair config generation with custom targets."""
    print("=== Testing generate_pairs_config() with custom targets ===\n")
    
    # Test 1: Default basket
    config1 = DataProcessor.generate_pairs_config(["ZAR"])
    print(f"Default basket: {len(config1)} pairs")
    
    # Test 2: Custom targets
    config2 = DataProcessor.generate_pairs_config(["ZAR"], ["USD", "EUR"])
    print(f"Custom (USD, EUR): {len(config2)} pairs")
    for c in config2:
        print(f"  {c['user_base']} -> {c['user_target']} ({c['calculation_mode']})")
    
    # Test 3: Major basket
    major = DataProcessor.MAJOR_BASKET
    config3 = DataProcessor.generate_pairs_config(["ZAR"], major)
    print(f"Major basket: {len(config3)} pairs")
    print()


if __name__ == "__main__":
    test_parse_targets()
    test_all_keyword()
    test_generate_pairs_config()
