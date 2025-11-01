#!/usr/bin/env python3
"""
Test script for the Odds API client.

This script verifies that the Odds API key is working correctly
by making a simple API call to fetch available odds.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.clients.odds_api_client import OddsApiClient, OddsApiError


def main():
    """Test the Odds API client with the configured API key."""
    # Load environment variables
    load_dotenv()

    api_key = os.getenv('ODDS_API_KEY')

    if not api_key:
        print("❌ ERROR: ODDS_API_KEY not found in environment variables")
        print("Please ensure .env file exists with ODDS_API_KEY set")
        return 1

    print("=" * 60)
    print("Testing Odds API Client")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    try:
        # Initialize client
        print("Initializing OddsApiClient...")
        client = OddsApiClient(api_key=api_key)
        print("✓ Client initialized successfully")
        print()

        # Test 1: Get available sports
        print("Test 1: Fetching available sports...")
        sports = client.get_sports()
        print(f"✓ Found {len(sports)} available sports")

        # Show first few sports
        if sports:
            print("  Sample sports:")
            for sport in sports[:5]:
                print(f"    - {sport.get('key')}: {sport.get('title')}")
        print()

        # Test 2: Get odds for a specific league (Premier League)
        print("Test 2: Fetching odds for Premier League (EPL)...")
        try:
            epl_odds = client.get_odds('EPL')
            print(f"✓ Found odds for {len(epl_odds)} matches")

            # Show first match with odds
            if epl_odds:
                match = epl_odds[0]
                print(f"  Sample match: {match.get('home_team')} vs {match.get('away_team')}")

                bookmakers = match.get('bookmakers', [])
                print(f"  Available bookmakers: {len(bookmakers)}")

                if bookmakers:
                    bm = bookmakers[0]
                    print(f"    Example ({bm.get('key')}):")
                    for market in bm.get('markets', []):
                        if market.get('key') == 'h2h':
                            outcomes = market.get('outcomes', [])
                            for outcome in outcomes:
                                print(f"      {outcome.get('name')}: {outcome.get('price')}")
        except OddsApiError as e:
            print(f"  ⚠ No active matches found for EPL: {e}")
        print()

        # Test 3: Get available bookmakers
        print("Test 3: Checking available bookmakers...")
        print(f"  Configured bookmakers: {len(client.BOOKMAKERS)}")
        for bm in client.BOOKMAKERS[:6]:
            print(f"    - {bm}")
        print(f"    ... and {len(client.BOOKMAKERS) - 6} more")
        print()

        # Test 4: Get supported leagues
        print("Test 4: Supported leagues...")
        print(f"  Configured leagues: {len(client.LEAGUE_IDS)}")
        for league_name, league_id in list(client.LEAGUE_IDS.items())[:5]:
            print(f"    - {league_name}: {league_id}")
        print(f"    ... and {len(client.LEAGUE_IDS) - 5} more")
        print()

        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        print()
        print("The Odds API key is working correctly.")
        print("You can now use the OddsApiClient in your application.")

        return 0

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return 1
    except OddsApiError as e:
        print(f"❌ API error: {e}")
        print("\nThis could be due to:")
        print("  - Invalid API key")
        print("  - Rate limit exceeded")
        print("  - Network connectivity issues")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
