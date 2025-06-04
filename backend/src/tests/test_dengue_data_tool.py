"""
Direct test of the DengueDataTool to retrieve data from the API.
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("dengue_data_tool_test")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import the tool
from backend.src.tools.dengue_data_tool import DengueDataTool

async def test_dengue_data_tool():
    """Test the DengueDataTool directly."""
    
    # Initialize the tool
    data_tool = DengueDataTool()
    
    # Get the available countries from the tool
    logger.info(f"Available API countries: {data_tool.available_countries}")
    
    # Test retrieving data for each available country
    for country in data_tool.available_countries:
        logger.info(f"Testing retrieval for country: {country}")
        
        # Historical data
        try:
            historical_data = await data_tool.get_historical_data(country)
            logger.info(f"Successfully retrieved historical data for {country}")
            logger.info(f"Data points: {len(historical_data.get('data', []))}")
        except Exception as e:
            logger.error(f"Error retrieving historical data for {country}: {str(e)}")
        
        # Future data
        try:
            # Test with a future date - 3 months from now
            today = datetime.now()
            future_date = f"{today.year}-{(today.month + 3) % 12 or 12:02d}-15"
            logger.info(f"Testing prediction with future date: {future_date}")
            
            future_data = await data_tool.get_prediction_data(country, future_date)
            logger.info(f"Successfully retrieved prediction data for {country}")
            logger.info(f"Prediction data points: {len(future_data.get('data', []))}")
        except Exception as e:
            logger.error(f"Error retrieving prediction data for {country}: {str(e)}")
        
        # Combined data with the get_dengue_data method
        try:
            combined_data = await data_tool.get_dengue_data(country, future_date)
            logger.info(f"Successfully retrieved combined data for {country}")
            logger.info(f"Historical points: {len(combined_data.get('historical_data', []))}")
            logger.info(f"Prediction points: {len(combined_data.get('predicted_data', []))}")
            
            # Save the data to a file for inspection
            with open(f"dengue_data_{country}.json", "w") as f:
                json.dump(combined_data, f, indent=2)
                logger.info(f"Saved combined data to dengue_data_{country}.json")
        except Exception as e:
            logger.error(f"Error retrieving combined data for {country}: {str(e)}")
        
        logger.info(f"Completed testing for {country}\n")

if __name__ == "__main__":
    asyncio.run(test_dengue_data_tool())
