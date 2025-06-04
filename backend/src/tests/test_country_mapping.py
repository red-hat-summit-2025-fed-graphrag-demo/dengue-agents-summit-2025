"""
Simple test script to verify the country mapping logic in the visualization agent.
"""

import sys
import os
import logging

# Configure logging to show DEBUG level messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Add parent directory to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import the agent
from backend.src.agent_system.rag_system.enhancement.dengue_data_visualization_agent import DengueDataVisualizationAgent

def test_country_mapping():
    """Test the country mapping function directly."""
    # Create a minimal config dictionary
    config = {
        "agent_id": "test_dengue_data_visualization_agent",
        "model_config": {
            "model_type": "instruct",
            "max_tokens": 512
        }
    }
    
    # Initialize the agent
    agent = DengueDataVisualizationAgent("test", config)
    
    # Test countries
    test_countries = [
        "Saudi Arabia",
        "saudi arabia", 
        "Saudi", 
        "Arabia", 
        "KSA",
        "Australia",
        "New Caledonia"
    ]
    
    print("\n=== Testing Country Mapping Logic ===")
    print(f"Agent country_mapping keys: {list(agent.country_mapping.keys())}")
    print(f"Is 'saudi arabia' in mapping keys? {'saudi arabia' in agent.country_mapping}")
    
    # Test each country
    for country in test_countries:
        api_country = agent._map_to_api_country(country)
        print(f"'{country}' -> '{api_country}'")
    
    # Test country extraction from a query
    test_query = "I have a patient who lives in New York and plans to travel to Saudi Arabia on September 1, 2025."
    country_mentions = agent._extract_country_mentions(test_query)
    print(f"\nCountries extracted from query: {country_mentions}")
    
    # Test mapping extracted countries
    print("\nMapping extracted countries:")
    for country in country_mentions:
        api_country = agent._map_to_api_country(country)
        print(f"'{country}' -> '{api_country}'")
    
if __name__ == "__main__":
    test_country_mapping()
