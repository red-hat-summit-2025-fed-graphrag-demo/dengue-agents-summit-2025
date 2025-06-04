"""
Tool for extracting dates from natural language text.

This tool uses regex and datetime parsing to identify and extract dates from natural language queries.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ExtractDatesFromNaturalLanguageTool:
    """
    ExtractDatesFromNaturalLanguageTool 
    
    This tool extracts dates from natural language text, including:
    - Explicit dates (May 15, 2025, 2025-05-15, etc.)
    - Relative dates (next month, tomorrow, etc.)
    - Date ranges (from May to September)
    - Named periods (summer, winter, etc.)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the ExtractDatesFromNaturalLanguageTool.
        
        Args:
            config: Tool configuration dictionary (optional)
        """
        self.id = "extract_dates_from_natural_language_tool"
        self.config = config or {}
        
        # Month name mappings
        self.month_names = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9, "sept": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }
        
        # Season mappings with approximate months
        self.season_mappings = {
            "spring": {"start_month": 3, "end_month": 5},
            "summer": {"start_month": 6, "end_month": 8},
            "fall": {"start_month": 9, "end_month": 11},
            "autumn": {"start_month": 9, "end_month": 11},
            "winter": {"start_month": 12, "end_month": 2}
        }
    
    async def _execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the provided parameters.
        
        Args:
            params: Dictionary of parameters for tool execution
                - text: The natural language text to extract dates from
            
        Returns:
            Dictionary containing the extracted dates and metadata
        """
        # Validate parameters
        self._validate_params(params)
        
        # Extract the text parameter
        text = params.get("text", "")
        
        # Extract dates from the text
        has_future_date, dates = self._extract_dates(text)
        
        # Create result
        result = {
            "has_future_date": has_future_date,
            "dates": dates,
            "text": text
        }
        
        # Return the result directly
        return {
            "tool_id": self.id,
            "status": "success",
            "result": result,
            "metadata": {"text_length": len(text)}
        }
    
    def _validate_params(self, params: Dict[str, Any]) -> None:
        """
        Validate that required parameters are present.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValueError: If required parameters are missing
        """
        if "text" not in params:
            raise ValueError("Missing required parameter: 'text'")
    
    def _extract_dates(self, text: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Extract dates from the provided text.
        
        Args:
            text: Natural language text to extract dates from
            
        Returns:
            Tuple containing:
                - Boolean indicating if a future date was found
                - List of extracted dates with metadata
        """
        logger.info(f"Extracting dates from text: {text[:100]}...")
        
        # Initialize results
        extracted_dates = []
        has_future_date = False
        
        # Get current date
        current_date = datetime.now()
        
        # Pattern for dates like "May 15, 2025" or "15 May 2025" or "15th of May, 2025"
        month_day_year_pattern = r'(?:(?:on|until|before|after|by|from|to)\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)(?:,?\s+(\d{4}))?|([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?'
        
        # Pattern for ISO dates like "2025-05-15"
        iso_date_pattern = r'(\d{4})-(\d{1,2})-(\d{1,2})'
        
        # Pattern for future references like "next month", "in 2 weeks"
        relative_pattern = r'(?:in|next|following|coming|after)\s+(\d+)?\s*([A-Za-z]+)'
        
        # Search for month-day-year patterns
        for match in re.finditer(month_day_year_pattern, text.lower()):
            try:
                # Extract components from the match
                if match.group(1):  # "15 May 2025" format
                    day = int(match.group(1))
                    month_str = match.group(2).lower()
                    year_str = match.group(3)
                else:  # "May 15, 2025" format
                    month_str = match.group(4).lower()
                    day = int(match.group(5))
                    year_str = match.group(6)
                
                # Convert month name to number
                if month_str in self.month_names:
                    month = self.month_names[month_str]
                else:
                    continue
                
                # Use current year if not specified
                year = int(year_str) if year_str else current_date.year
                
                # Create date
                try:
                    date_obj = datetime(year, month, day)
                    
                    # Check if it's in the future
                    if date_obj > current_date:
                        has_future_date = True
                    
                    # Add to results
                    extracted_dates.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "type": "explicit",
                        "is_future": date_obj > current_date,
                        "match": match.group(0)
                    })
                except ValueError:
                    # Invalid date (e.g., February 30)
                    pass
            except Exception as e:
                logger.error(f"Error processing date match '{match.group(0)}': {str(e)}")
        
        # Search for ISO dates
        for match in re.finditer(iso_date_pattern, text):
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                
                # Create date
                try:
                    date_obj = datetime(year, month, day)
                    
                    # Check if it's in the future
                    if date_obj > current_date:
                        has_future_date = True
                    
                    # Add to results
                    extracted_dates.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "type": "iso",
                        "is_future": date_obj > current_date,
                        "match": match.group(0)
                    })
                except ValueError:
                    # Invalid date
                    pass
            except Exception as e:
                logger.error(f"Error processing ISO date match '{match.group(0)}': {str(e)}")
        
        # Search for relative dates
        for match in re.finditer(relative_pattern, text.lower()):
            try:
                # Get the quantity (default to 1 if not specified)
                quantity = int(match.group(1)) if match.group(1) else 1
                unit = match.group(2).lower().rstrip('s')  # Remove trailing 's' if present
                
                # Calculate the date
                if unit in ['day', 'daily']:
                    date_obj = current_date + timedelta(days=quantity)
                elif unit in ['week', 'weekly']:
                    date_obj = current_date + timedelta(weeks=quantity)
                elif unit in ['month', 'monthly']:
                    # Add months (approximate)
                    new_month = current_date.month + quantity
                    new_year = current_date.year + ((new_month - 1) // 12)
                    new_month = ((new_month - 1) % 12) + 1
                    date_obj = datetime(new_year, new_month, min(current_date.day, 28))
                elif unit in ['year', 'annual', 'annually']:
                    date_obj = datetime(current_date.year + quantity, current_date.month, current_date.day)
                else:
                    # Not a recognized time unit
                    continue
                
                # All relative dates should be in the future
                has_future_date = True
                
                # Add to results
                extracted_dates.append({
                    "date": date_obj.strftime("%Y-%m-%d"),
                    "type": "relative",
                    "is_future": True,
                    "match": match.group(0)
                })
            except Exception as e:
                logger.error(f"Error processing relative date match '{match.group(0)}': {str(e)}")
        
        # Check for seasons
        season_pattern = r'(?:in|during|this|next)\s+(?:the\s+)?([A-Za-z]+)'
        for match in re.finditer(season_pattern, text.lower()):
            season = match.group(1).lower()
            if season in self.season_mappings:
                try:
                    season_info = self.season_mappings[season]
                    start_month = season_info["start_month"]
                    end_month = season_info["end_month"]
                    
                    # Determine the year based on current date
                    year = current_date.year
                    if current_date.month > end_month:
                        # If we've passed this season in the current year, use next year
                        if "next" in match.group(0).lower():
                            year += 1
                    
                    # Use the middle of the season
                    if start_month > end_month:  # Winter crosses year boundary
                        month = (start_month + 12 + end_month) // 2
                        if month > 12:
                            month -= 12
                    else:
                        month = (start_month + end_month) // 2
                    
                    # Use the middle of the month
                    date_obj = datetime(year, month, 15)
                    
                    # Check if it's in the future
                    if date_obj > current_date:
                        has_future_date = True
                    
                    # Add to results
                    extracted_dates.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "type": "season",
                        "is_future": date_obj > current_date,
                        "match": match.group(0),
                        "season": season
                    })
                except Exception as e:
                    logger.error(f"Error processing season match '{match.group(0)}': {str(e)}")
        
        # Sort dates chronologically
        extracted_dates.sort(key=lambda x: x["date"])
        
        logger.info(f"Extracted {len(extracted_dates)} dates, has_future_date: {has_future_date}")
        return has_future_date, extracted_dates
