#!/usr/bin/env python3
"""
Test script to verify MTL Translation Tools setup
"""

import json
import os
import sys
import requests

# Handle TOML imports for different Python versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from pathlib import Path


def test_config():
    """Test if config.toml exists and is valid."""
    print("Testing config.toml...")
    if tomllib is None:
        print("  ✗ tomli/tomllib not installed (run: pip install tomli)")
        return None

    try:
        with open('config.toml', 'rb') as f:
            config = tomllib.load(f)
        print("  ✓ config.toml loaded successfully")
        if config.get('translation_settings', {}).get('context_lines', 0) > 0:
            print(f"  ✓ Context lines enabled: {config['translation_settings']['context_lines']}")
        return config
    except FileNotFoundError:
        print("  ✗ config.toml not found")
        return None
    except Exception as e:
        print(f"  ✗ config.toml is invalid: {e}")
        return None


def test_dictionary():
    """Test if dictionary.json exists and is valid."""
    print("\nTesting dictionary.json...")
    try:
        with open('dictionary.json', 'r', encoding='utf-8') as f:
            dictionary = json.load(f)
        print(f"  ✓ dictionary.json loaded with {len(dictionary)} entries")
        return True
    except FileNotFoundError:
        print("  ✗ dictionary.json not found")
        return False
    except json.JSONDecodeError as e:
        print(f"  ✗ dictionary.json is invalid: {e}")
        return False


def test_folders(config):
    """Test if required folders exist."""
    print("\nTesting folder structure...")

    input_folder = config['translation_settings']['input_folder']
    output_folder = config['translation_settings']['output_folder']

    if os.path.exists(input_folder):
        json_files = list(Path(input_folder).rglob('*.json'))
        print(f"  ✓ Input folder '{input_folder}' exists with {len(json_files)} JSON files")
    else:
        print(f"  ⚠ Input folder '{input_folder}' not found (will be created if needed)")

    if os.path.exists(output_folder):
        print(f"  ✓ Output folder '{output_folder}' exists")
    else:
        print(f"  ⚠ Output folder '{output_folder}' not found (will be created)")


def test_llm_connection(config):
    """Test connection to LLM API."""
    print("\nTesting LLM connection...")

    llm_config = config['llm_settings']
    api_url = llm_config['api_url']

    # Try to reach the API
    try:
        # Test with a simple request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_config['api_key']}"
        }

        payload = {
            "model": llm_config['model'],
            "messages": [
                {"role": "system", "content": "You are a translator."},
                {"role": "user", "content": "Translate to English: テスト"}
            ],
            "temperature": 0.3,
            "max_tokens": 50
        }

        print(f"  Attempting connection to {api_url}...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content']
            print(f"  ✓ LLM connection successful!")
            print(f"  ✓ Test translation: テスト -> {translation}")
            return True
        else:
            print(f"  ✗ LLM returned status code {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"  ✗ Could not connect to {api_url}")
        print("    Make sure your LLM server (LM Studio, etc.) is running")
        return False
    except requests.exceptions.Timeout:
        print(f"  ✗ Connection timed out")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_dependencies():
    """Test if required Python packages are installed."""
    print("\nTesting Python dependencies...")

    try:
        import requests
        print("  ✓ requests installed")
    except ImportError:
        print("  ✗ requests not installed (run: pip install requests)")

    try:
        import openpyxl
        print("  ✓ openpyxl installed")
    except ImportError:
        print("  ✗ openpyxl not installed (run: pip install openpyxl)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MTL Translation Tools - Setup Test")
    print("=" * 60)

    test_dependencies()

    config = test_config()
    if not config:
        print("\n✗ Setup incomplete. Please create/fix config.json")
        return

    test_dictionary()

    from pathlib import Path
    test_folders(config)

    # Only test LLM if user confirms
    test_llm = input("\nTest LLM connection? (y/n): ").strip().lower()
    if test_llm == 'y':
        test_llm_connection(config)

    print("\n" + "=" * 60)
    print("Setup test complete!")
    print("=" * 60)
    print("\nIf all tests passed, you're ready to run:")
    print("  python main.py")


if __name__ == "__main__":
    main()
