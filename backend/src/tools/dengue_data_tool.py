"""
Dengue Data Tool

This tool interfaces with the Dengue Fever Prediction Service API to retrieve
historical data and predictions for dengue fever cases.
"""
import os
import httpx
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class DengueDataTool:
    """Tool to interact with the Dengue Fever Prediction Service API."""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize the DengueDataTool.
        
        Args:
            api_url: The URL for the dengue prediction service API
        """
        self.api_url = api_url or os.environ.get("DENGUE_DATA_URL", "https://dengue-prediction-service-model-service-dengue.apps.cluster-8gvkk.8gvkk.sandbox888.opentlc.com")
        # Ensure URL doesn't have a trailing slash
        self.api_url = self.api_url.rstrip('/')
        
        # Available countries in the dataset based on the API response
        self.available_countries = ["australia", "new_caledonia", "saudi_arabia"]
        
        # Map common country names or regions to available API countries
        self.country_mapping = {
            # Map to australia
            "australia": "australia",
            "sydney": "australia",
            "melbourne": "australia",
            "brisbane": "australia",
            "oceania": "australia",
            
            # Map to new_caledonia
            "new caledonia": "new_caledonia",
            "new-caledonia": "new_caledonia",
            "caledonia": "new_caledonia",
            "pacific": "new_caledonia",
            "pacific islands": "new_caledonia",
            "noumea": "new_caledonia",
            
            # Map to saudi_arabia
            "saudi arabia": "saudi_arabia",
            "saudi-arabia": "saudi_arabia",
            "saudi": "saudi_arabia",
            "riyadh": "saudi_arabia",
            "jeddah": "saudi_arabia",
            "middle east": "saudi_arabia",
            "arabia": "saudi_arabia",
            
            # Default mappings for common dengue regions that aren't available
            # Map common southeast Asian countries to the closest available region
            "thailand": "australia",  # Use Australia as a proxy for Thailand
            "singapore": "australia",
            "malaysia": "australia",
            "indonesia": "australia",
            "philippines": "new_caledonia",  # Use New Caledonia as a proxy for Philippines
            "vietnam": "new_caledonia",
            "cambodia": "new_caledonia",
            "laos": "new_caledonia",
            "myanmar": "new_caledonia",
            "india": "saudi_arabia",  # Use Saudi Arabia as a proxy for India
            "pakistan": "saudi_arabia",
            "bangladesh": "saudi_arabia",
            "sri lanka": "saudi_arabia"
        }
        
        logger.info(f"Initialized DengueDataTool with API URL: {self.api_url}")
        logger.info(f"Available countries: {self.available_countries}")
    
    def _map_country_name(self, country: str) -> str:
        """
        Map a user-provided country name to an available API country.
        
        Args:
            country: The country name provided by the user
            
        Returns:
            The mapped country name that can be used with the API
        """
        country_lower = country.lower()
        
        # Direct match with available countries
        if country_lower in self.available_countries:
            return country_lower
            
        # Check mapping dictionary
        if country_lower in self.country_mapping:
            mapped_country = self.country_mapping[country_lower]
            logger.info(f"Mapped country '{country}' to API country '{mapped_country}'")
            return mapped_country
            
        # Default to Australia if no mapping found
        logger.warning(f"No mapping found for country '{country}'. Using 'australia' as default.")
        return "australia"
    
    async def get_historical_data(self, country: str) -> Dict[str, Any]:
        """
        Get historical dengue data for a specific country.
        
        Args:
            country: The country to retrieve data for (must be one of the available countries)
            
        Returns:
            A dictionary containing the historical data
        """
        # Map the country name to an available API country
        api_country = self._map_country_name(country)
        
        endpoint = f"{self.api_url}/historical/{api_country}"
        logger.info(f"Fetching historical data for {country} (mapped to {api_country}) from {endpoint}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                result = response.json()
                
                # Log detailed statistics about the data
                historical_data = result.get("data", [])
                logger.info(f"Retrieved historical data for {country} (API: {api_country}):")
                logger.info(f"  Historical data points: {len(historical_data)}")
                
                # Log first and last points of each dataset for verification
                if historical_data:
                    logger.info(f"  First historical data point: {json.dumps(historical_data[0])}")
                    logger.info(f"  Last historical data point: {json.dumps(historical_data[-1])}")
                
                # Add original country for context
                result["requested_country"] = country
                result["mapped_country"] = api_country
                
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error fetching historical data: {str(e)}")
                return {
                    "error": str(e), 
                    "requested_country": country,
                    "mapped_country": api_country
                }
    
    async def get_predictions(self, country: str, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get predicted dengue cases for a country up to a specified end date.
        
        Args:
            country: The country to retrieve predictions for (will be mapped to available API countries)
            end_date: The end date for predictions in YYYY-MM-DD format
                     If not provided, uses May 22, 2025 or current date + 30 days, whichever is later
            
        Returns:
            A dictionary containing historical and predicted data
        """
        # Map the country name to an available API country
        api_country = self._map_country_name(country)
        
        # If no end date is provided, use the later of May 22, 2025 or current date + 30 days
        if not end_date:
            presentation_date = datetime(2025, 5, 22)
            current_date = datetime.now()
            future_date = current_date + timedelta(days=30)
            
            # Use the later date
            if presentation_date > future_date:
                end_date = presentation_date.strftime("%Y-%m-%d")
            else:
                end_date = future_date.strftime("%Y-%m-%d")
        
        endpoint = f"{self.api_url}/predict/{api_country}?end_date={end_date}"
        logger.info(f"Fetching predictions for {country} (mapped to {api_country}) until {end_date} from {endpoint}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(endpoint)
                response.raise_for_status()
                result = response.json()
                
                # Log detailed statistics about the data
                historical_data = result.get("historical_data", [])
                predicted_data = result.get("predicted_data", [])
                logger.info(f"Retrieved prediction data for {country} (API: {api_country}):")
                logger.info(f"  Historical data points: {len(historical_data)}")
                logger.info(f"  Predicted data points: {len(predicted_data)}")
                
                # Log first and last points of each dataset for verification
                if historical_data:
                    logger.info(f"  First historical data point: {json.dumps(historical_data[0])}")
                    logger.info(f"  Last historical data point: {json.dumps(historical_data[-1])}")
                
                if predicted_data:
                    logger.info(f"  First predicted data point: {json.dumps(predicted_data[0])}")
                    logger.info(f"  Last predicted data point: {json.dumps(predicted_data[-1])}")
                
                # Add original country for context
                result["requested_country"] = country
                result["mapped_country"] = api_country
                
                return result
            except httpx.HTTPError as e:
                logger.error(f"Error fetching predictions: {str(e)}")
                return {
                    "error": str(e), 
                    "requested_country": country,
                    "mapped_country": api_country
                }
    
    async def get_dengue_data(self, country: str, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete dengue data including both historical and predicted data.
        This is an alias method to match the API expected by the visualization agent.
        
        Args:
            country: The country to retrieve data for
            time_period: A future date string (YYYY-MM-DD) to predict to
            
        Returns:
            A dictionary containing both historical and predicted data
        """
        logger.info(f"get_dengue_data called for country '{country}', time_period: '{time_period}'")
        
        # If time_period is provided, use it as the end_date for predictions
        if time_period:
            return await self.get_predictions(country, time_period)
        else:
            # Get historical data only
            historical_data = await self.get_historical_data(country)
            
            # Format in the same way predictions would be returned
            return {
                "country": country,
                "mapped_country": self._map_country_name(country),
                "historical_data": historical_data.get("data", []),
                "predicted_data": [],
                "requested_country": country
            }
    
    async def get_visualization_data(self, country: str, visualization_period: int = 60) -> Dict[str, Any]:
        """
        Get data suitable for visualization, including both historical and predicted data.
        
        Args:
            country: The country to retrieve data for (will be mapped to available API countries)
            visualization_period: Number of days to include in visualization (from past through future)
            
        Returns:
            A dictionary containing data ready for visualization
        """
        # Map the country name to an available API country
        api_country = self._map_country_name(country)
        
        # Set the end date to ensure we have data for the presentation (May 22, 2025)
        # Ensure this is at least 30 days in the future from the current date
        presentation_date = datetime(2025, 5, 22)
        current_date = datetime.now()
        future_date = current_date + timedelta(days=30)
        
        # Use the later date
        if presentation_date > future_date:
            end_date = presentation_date.strftime("%Y-%m-%d")
        else:
            end_date = future_date.strftime("%Y-%m-%d")
            
        # Get predictions which include historical data
        prediction_data = await self.get_predictions(country, end_date)
        
        if "error" in prediction_data:
            logger.error(f"Error retrieving prediction data for {country}: {prediction_data['error']}")
            return prediction_data
        
        # Log detailed statistics about the data
        historical_data = prediction_data.get("historical_data", [])
        predicted_data = prediction_data.get("predicted_data", [])
        
        logger.info(f"Retrieved data for {country} (API: {api_country}):")
        logger.info(f"  Historical data points: {len(historical_data)}")
        logger.info(f"  Predicted data points: {len(predicted_data)}")
        
        # Log first and last points of each dataset for verification
        if historical_data:
            logger.info(f"  First historical data point: {json.dumps(historical_data[0])}")
            logger.info(f"  Last historical data point: {json.dumps(historical_data[-1])}")
        
        if predicted_data:
            logger.info(f"  First predicted data point: {json.dumps(predicted_data[0])}")
            logger.info(f"  Last predicted data point: {json.dumps(predicted_data[-1])}")
        
        # Extract relevant information for visualization
        result = {
            "country": country,
            "api_country": api_country,
            "current_date": current_date.strftime("%Y-%m-%d"),
            "presentation_date": "2025-05-22",  # Fixed for the presentation
            "historical_data": historical_data,
            "predicted_data": predicted_data,
            "visualization_code": self._generate_visualization_code(country, api_country)
        }
        
        return result
    
    def _generate_visualization_code(self, country: str, api_country: str) -> str:
        """
        Generate Python code for visualizing dengue data.
        
        Args:
            country: The original requested country
            api_country: The API country used for data retrieval
            
        Returns:
            Python code as a string for creating the visualization
        """
        # Use triple-quotes with the r prefix to avoid escaping issues
        code = r"""
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
from datetime import datetime
import json

# Function to parse the data and create a visualization
def create_dengue_visualization(data, country="%s", api_country="%s", output_file="dengue_forecast.png"):
    # Extract historical and predicted data
    historical_data = data.get("historical_data", [])
    predicted_data = data.get("predicted_data", [])
    
    # Convert to DataFrames
    hist_df = pd.DataFrame(historical_data)
    pred_df = pd.DataFrame(predicted_data)
    
    # Convert date strings to datetime objects
    hist_df["date"] = pd.to_datetime(hist_df["date"])
    pred_df["date"] = pd.to_datetime(pred_df["date"])
    
    # Sort by date
    hist_df = hist_df.sort_values("date")
    pred_df = pred_df.sort_values("date")
    
    # Create figure and axis
    plt.figure(figsize=(12, 6))
    
    # Plot historical data
    plt.plot(hist_df["date"], hist_df["cases"], color="blue", label="Historical Cases")
    
    # Plot predicted data
    plt.plot(pred_df["date"], pred_df["cases"], color="red", linestyle="--", label="Predicted Cases")
    
    # Set labels and title
    plt.xlabel("Date")
    plt.ylabel("Dengue Cases")
    
    # Create an informative title that explains the data source
    title = f"Dengue Fever Cases Forecast for {country}"
    if country.lower() != api_country.lower():
        title += f"\n(Using data from {api_country.title()} as proxy)"
    plt.title(title)
    
    # Format date axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%%Y-%%m-%%d"))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gcf().autofmt_xdate()
    
    # Add legend
    plt.legend()
    
    # Add grid
    plt.grid(True, alpha=0.3)
    
    # Highlight the current period of interest (e.g., September for Thailand travel)
    if country.lower() == "thailand" and any(pd.to_datetime("2025-09-01") <= date <= pd.to_datetime("2025-09-30") for date in pred_df["date"]):
        sept_data = pred_df[(pred_df["date"] >= "2025-09-01") & (pred_df["date"] <= "2025-09-30")]
        if not sept_data.empty:
            plt.axvspan(pd.to_datetime("2025-09-01"), pd.to_datetime("2025-09-30"), 
                       alpha=0.2, color="yellow", label="Travel Period (September)")
            
            # Get the average cases for September
            sept_avg = sept_data["cases"].mean()
            
            # Add annotation for September average
            plt.annotate(f"September Avg: {sept_avg:.1f} cases/day", 
                        xy=(pd.to_datetime("2025-09-15"), sept_avg),
                        xytext=(pd.to_datetime("2025-09-15"), sept_avg + 20),
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3", color="black"),
                        bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.3))
    
    # Add note about data sources
    plt.figtext(0.5, 0.01, 
                "Note: This visualization uses proxy data and should be used for illustrative purposes only.", 
                ha="center", fontsize=9, style="italic")
    
    # Save the figure
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()
    
    return output_file

# Example usage:
# with open('dengue_data.json', 'r') as f:
#     data = json.load(f)
# create_dengue_visualization(data)
""" % (country, api_country)
        
        return code


# Test the tool if run directly
if __name__ == "__main__":
    async def test():
        tool = DengueDataTool()
        
        # Test API info
        print(f"API URL: {tool.api_url}")
        print(f"Available countries: {tool.available_countries}")
        
        # Test country mapping
        test_countries = ["Thailand", "Australia", "New Caledonia", "Saudi Arabia", "Indonesia", "Philippines", "Unknown"]
        for country in test_countries:
            mapped = tool._map_country_name(country)
            print(f"'{country}' maps to '{mapped}'")
        
        # Test getting historical data for Australia
        historical_data = await tool.get_historical_data("Australia")
        print(f"\nHistorical data for Australia (first 3 entries):")
        if "data" in historical_data and len(historical_data.get("data", [])) > 0:
            print(json.dumps(historical_data.get("data", [])[:3], indent=2))
        else:
            print(f"Error or no data: {historical_data}")
        
        # Test getting predictions for Australia
        predictions = await tool.get_predictions("Australia")
        print(f"\nPredictions for Australia (sample entries):")
        if "error" not in predictions:
            print("Historical (first 3):")
            print(json.dumps(predictions.get("historical_data", [])[:3], indent=2))
            print("Predicted (first 3):")
            print(json.dumps(predictions.get("predicted_data", [])[:3], indent=2))
        else:
            print(f"Error: {predictions}")
            
        # Test mapped country (Thailand -> Australia)
        predictions = await tool.get_predictions("Thailand")
        print(f"\nPredictions for Thailand (using mapped data):")
        if "error" not in predictions:
            print(f"Mapped to: {predictions.get('mapped_country')}")
            if predictions.get("historical_data") and predictions.get("predicted_data"):
                print(f"Historical data points: {len(predictions.get('historical_data', []))}")
                print(f"Predicted data points: {len(predictions.get('predicted_data', []))}")
        else:
            print(f"Error: {predictions}")
        
    asyncio.run(test())
