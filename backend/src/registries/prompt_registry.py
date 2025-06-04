"""
Prompt Registry

A registry for managing and accessing prompts stored as YAML files.
Provides functionality to load, format, and retrieve prompts.

This registry implements the BaseRegistry abstract class to ensure
a consistent interface with other registries in the system.
"""
import os
import glob
import yaml
import logging
import re
from typing import Dict, List, Optional, Any, Set, Union

from src.registries.base_registry import BaseRegistry
from src.registries.registry_validator import PromptRegistryValidator

logger = logging.getLogger(__name__)

class PromptRegistry(BaseRegistry):
    """
    A registry for managing prompts stored as YAML files.
    
    This registry loads prompts from YAML files, indexes them by ID,
    and provides methods to retrieve and format them for use in agents.
    Inherits from BaseRegistry to ensure a consistent interface with other registries.
    """
    
    def __init__(self, base_dir: Optional[str] = None, registry_path: Optional[str] = None):
        """
        Initialize the PromptRegistry.
        
        Args:
            base_dir: Optional base directory for prompt files. If not provided,
                     defaults to the 'prompts' directory in the current package.
            registry_path: Optional path to a registry index file. For PromptRegistry,
                         this is not typically used as prompts are loaded from individual files.
        """
        super().__init__(base_dir=base_dir, registry_path=registry_path)
    
    def _get_default_base_dir(self) -> str:
        """Get the default base directory for prompt files."""
        return "prompts"
    
    def _get_default_registry_path(self) -> str:
        """Get the default registry file path."""
        # PromptRegistry typically doesn't use a central registry file,
        # but we provide a default path for compatibility
        return os.path.join(os.path.dirname(__file__), "prompts", "registry.json")
    
    def _get_validator(self) -> PromptRegistryValidator:
        """Get the validator for prompt registry entries."""
        return PromptRegistryValidator()
    
    def _load_registry(self) -> None:
        """Load prompts from YAML files in the base directory."""
        # Use the helper method from BaseRegistry to load from directory
        self._load_directory_registry(file_extension=".yaml", key_field="id")
        
        # Additional check for the required 'prompt' field - this is a critical field
        # that might not be caught by the validator if it's empty but present
        for item_id, item_data in list(self._registry_items.items()):
            if not item_data.get('prompt'):
                logger.warning(f"Prompt '{item_id}' is missing required 'prompt' field - skipping")
                self._registry_items.pop(item_id, None)
    
    def get_prompt(self, prompt_id: str, **kwargs) -> str:
        """
        Get a prompt by ID and format it with the provided kwargs.
        
        Args:
            prompt_id: The ID of the prompt to retrieve
            **kwargs: Variables to insert into the prompt template
            
        Returns:
            The formatted prompt string
            
        Raises:
            ValueError: If the prompt ID is not found
        """
        try:
            # Use BaseRegistry's get_item method
            prompt_data = self.get_item(prompt_id)
            prompt_template = prompt_data["prompt"]
            
            # Format prompt template using variable placeholders like {{variable}}
            for key, value in kwargs.items():
                pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
                prompt_template = re.sub(pattern, str(value), prompt_template)
            
            return prompt_template
        except ValueError:
            raise ValueError(f"Prompt '{prompt_id}' not found")
    
    def get_prompt_metadata(self, prompt_id: str) -> Dict[str, Any]:
        """
        Get the metadata for a prompt by ID.
        
        Args:
            prompt_id: The ID of the prompt
            
        Returns:
            A dictionary containing the prompt metadata
            
        Raises:
            ValueError: If the prompt ID is not found
        """
        try:
            # Use BaseRegistry's get_item method
            prompt_data = self.get_item(prompt_id).copy()
            # Remove the actual prompt text from the metadata
            prompt_data.pop("prompt", None)
            return prompt_data
        except ValueError:
            raise ValueError(f"Prompt '{prompt_id}' not found")
    
    def list_prompts(self, tags: Optional[Union[str, List[str]]] = None, 
                     model: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List prompts, optionally filtered by tags or model.
        
        Args:
            tags: Optional tag or list of tags to filter by
            model: Optional model name to filter by
            
        Returns:
            A list of prompt metadata dictionaries
        """
        # Convert single tag to list for consistency
        if isinstance(tags, str):
            tags = [tags]
        
        # Define filter function based on the provided criteria
        def filter_func(item: Dict[str, Any]) -> bool:
            # Filter by tags if specified
            if tags and not any(tag in item.get("tags", []) for tag in tags):
                return False
                
            # Filter by model if specified
            if model and model not in item.get("models", []):
                return False
                
            return True
        
        # Use BaseRegistry list_items with our filter
        items = self.list_items(filter_func=filter_func)
        
        # Remove prompt text from each item
        for item in items:
            item.pop("prompt", None)
            
        return items
    
    def get_prompt_by_tags(self, tags: Union[str, List[str]], 
                          model: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find prompts with specific tags, optionally filtered by model.
        
        Args:
            tags: Tag or list of tags to search for
            model: Optional model name to filter by
            
        Returns:
            A list of matching prompt metadata dictionaries
        """
        return self.list_prompts(tags=tags, model=model)
    
    def register_prompt(self, prompt_id: str, prompt_text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Register a new prompt.
        
        Args:
            prompt_id: The ID to use for the prompt
            prompt_text: The prompt template text
            metadata: Optional additional metadata for the prompt
            
        Returns:
            The ID of the registered prompt
        """
        # Create the full prompt item
        prompt_item = metadata.copy() if metadata else {}
        prompt_item.update({
            "id": prompt_id,
            "prompt": prompt_text
        })
        
        # Use the BaseRegistry register_item method
        return self.register_item(prompt_item, id_field="id")