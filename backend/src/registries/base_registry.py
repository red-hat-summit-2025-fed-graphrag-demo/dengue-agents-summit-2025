"""
Base Registry

Abstract base class that defines the common interface for all registry types.
Provides consistent patterns for loading, accessing, and managing registered resources.
"""
import os
import json
import yaml
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Union, Type

from src.registries.registry_validator import RegistryValidator, ValidationSeverity

logger = logging.getLogger(__name__)

class BaseRegistry(ABC):
    """
    Abstract base class for all registry implementations.
    
    This defines the common interface that all registry types must implement,
    ensuring consistent patterns across the system.
    """
    
    def __init__(self, registry_path: Optional[str] = None, base_dir: Optional[str] = None):
        """
        Initialize the base registry.
        
        Args:
            registry_path: Optional path to the registry file
            base_dir: Optional base directory for registry resources
        """
        # Set default paths if not provided
        self.base_dir = base_dir or os.path.join(os.path.dirname(__file__), self._get_default_base_dir())
        self.registry_path = registry_path or self._get_default_registry_path()
        
        # The primary storage for registry items
        self._registry_items: Dict[str, Dict[str, Any]] = {}
        
        # Cache for instantiated items
        self._instances: Dict[str, Any] = {}
        
        # Load the registry
        self._load_registry()
        
    @abstractmethod
    def _get_default_base_dir(self) -> str:
        """
        Get the default base directory for this registry type.
        
        Returns:
            Default base directory name
        """
        pass
    
    @abstractmethod
    def _get_default_registry_path(self) -> str:
        """
        Get the default registry file path for this registry type.
        
        Returns:
            Default registry file path
        """
        pass
    
    @abstractmethod
    def _get_validator(self) -> RegistryValidator:
        """
        Get the appropriate validator for this registry type.
        
        Returns:
            A RegistryValidator instance specific to this registry type
        """
        pass
    
    @abstractmethod
    def _load_registry(self) -> None:
        """
        Load the registry from storage.
        
        This method should populate self._registry_items with the loaded data.
        """
        pass
    
    def _load_json_registry(self, key_field: str = "id", items_field: str = None) -> None:
        """
        Helper method to load a JSON registry file.
        
        Args:
            key_field: The field in each item to use as the registry key
            items_field: Optional field in the JSON that contains the items list
        """
        if not os.path.exists(self.registry_path):
            logger.warning(f"Registry file not found at {self.registry_path}")
            return
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            # If the items are in a specific field, extract them
            items = registry_data
            if items_field and items_field in registry_data:
                items = registry_data[items_field]
            
            # Get the validator for this registry type
            validator = self._get_validator()
            invalid_count = 0
            
            # If items is a list, convert to dictionary using the key_field
            if isinstance(items, list):
                for item in items:
                    if key_field not in item:
                        logger.warning(f"Skipping item - missing '{key_field}' field")
                        continue
                    
                    item_id = item[key_field]
                    
                    # Validate the item
                    validation_result = validator.validate(item)
                    if not validation_result.is_valid:
                        invalid_count += 1
                        logger.warning(f"Item '{item_id}' failed validation but will be loaded. Run validation utility to fix issues.")
                        # Log detailed validation issues at debug level
                        for issue_msg in validation_result.get_formatted_issues():
                            logger.debug(f"Item '{item_id}': {issue_msg}")
                    
                    self._registry_items[item_id] = item
                    logger.debug(f"Loaded item '{item_id}'")
            else:
                # If items is already a dictionary, use it directly
                # In this case, we validate each item in the dictionary
                for item_id, item in items.items():
                    validation_result = validator.validate(item)
                    if not validation_result.is_valid:
                        invalid_count += 1
                        logger.warning(f"Item '{item_id}' failed validation but will be loaded. Run validation utility to fix issues.")
                        # Log detailed validation issues at debug level
                        for issue_msg in validation_result.get_formatted_issues():
                            logger.debug(f"Item '{item_id}': {issue_msg}")
                
                self._registry_items = items
                
            logger.info(f"Loaded {len(self._registry_items)} items from registry")
            if invalid_count > 0:
                logger.warning(f"{invalid_count} items failed validation but were loaded for backward compatibility")
            
        except Exception as e:
            logger.error(f"Error loading registry from {self.registry_path}: {str(e)}")
    
    def _load_directory_registry(self, file_extension: str, key_field: str = "id") -> None:
        """
        Helper method to load registry items from individual files in a directory.
        
        Args:
            file_extension: The file extension to look for (e.g., '.yaml', '.json')
            key_field: The field in each item to use as the registry key
        """
        import glob
        
        pattern = os.path.join(self.base_dir, "**", f"*{file_extension}")
        files = glob.glob(pattern, recursive=True)
        
        if not files:
            logger.warning(f"No {file_extension} files found in {self.base_dir}")
            return
        
        logger.info(f"Loading {len(files)} files from {self.base_dir}")
        
        # Get the validator for this registry type
        validator = self._get_validator()
        invalid_count = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if file_extension.lower() in ('.yaml', '.yml'):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                # Validate required fields
                if not data.get(key_field):
                    logger.warning(f"Skipping file {file_path} - missing '{key_field}' field")
                    continue
                
                item_id = data[key_field]
                
                # Validate the item
                validation_result = validator.validate(data)
                if not validation_result.is_valid:
                    invalid_count += 1
                    logger.warning(f"Item '{item_id}' from {file_path} failed validation but will be loaded. Run validation utility to fix issues.")
                    # Log detailed validation issues at debug level
                    for issue_msg in validation_result.get_formatted_issues():
                        logger.debug(f"Item '{item_id}': {issue_msg}")
                
                # Add to registry
                self._registry_items[item_id] = data
                logger.debug(f"Loaded '{item_id}' from {file_path}")
                
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {str(e)}")
        
        logger.info(f"Loaded {len(self._registry_items)} items from files")
        if invalid_count > 0:
            logger.warning(f"{invalid_count} items failed validation but were loaded for backward compatibility")
    
    def get_item(self, item_id: str) -> Dict[str, Any]:
        """
        Get a registry item by ID.
        
        Args:
            item_id: The ID of the item to retrieve
            
        Returns:
            The registry item
            
        Raises:
            ValueError: If the item ID is not found
        """
        if item_id not in self._registry_items:
            raise ValueError(f"Item '{item_id}' not found in registry")
        
        return self._registry_items[item_id].copy()
    
    def list_items(self, filter_func: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        List all registry items, optionally filtered.
        
        Args:
            filter_func: Optional filter function that takes an item and returns boolean
            
        Returns:
            A list of registry items
        """
        items = []
        
        for item_id, item_data in self._registry_items.items():
            # Apply filter if provided
            if filter_func and not filter_func(item_data):
                continue
                
            # Add a copy of the item
            items.append(self.get_item(item_id))
            
        return items
    
    def reload(self) -> None:
        """
        Reload the registry from storage.
        
        This clears any cached data and reloads from the source.
        """
        self._registry_items = {}
        self._instances = {}
        self._load_registry()
        
    def validate_item(self, item: Dict[str, Any]) -> bool:
        """
        Validate a registry item against the schema.
        
        Args:
            item: The registry item to validate
            
        Returns:
            True if the item is valid, False otherwise
        """
        # Get the validator for this registry type
        validator = self._get_validator()
        
        # Validate the item
        result = validator.validate(item)
        
        # Log validation issues
        for issue in result.issues:
            field = issue["field"]
            message = issue["message"]
            severity = issue["severity"]
            
            if severity == ValidationSeverity.ERROR:
                logger.error(f"Validation error for item '{item.get('id', 'unknown')}': {field} - {message}")
            elif severity == ValidationSeverity.WARNING:
                logger.warning(f"Validation warning for item '{item.get('id', 'unknown')}': {field} - {message}")
            else:  # ValidationSeverity.INFO
                logger.info(f"Validation info for item '{item.get('id', 'unknown')}': {field} - {message}")
        
        return result.is_valid
    
    def register_item(self, item: Dict[str, Any], id_field: str = "id") -> str:
        """
        Register a new item in the registry.
        
        Args:
            item: The item to register
            id_field: The field to use as the item ID
            
        Returns:
            The ID of the registered item
            
        Raises:
            ValueError: If the item is missing the ID field or fails validation
        """
        if id_field not in item:
            raise ValueError(f"Item is missing required '{id_field}' field")
        
        # Validate the item before registration
        if not self.validate_item(item):
            raise ValueError(f"Item '{item.get(id_field)}' failed validation")
        
        item_id = item[id_field]
        self._registry_items[item_id] = item.copy()
        
        # Persist the changes
        self._save_registry()
        
        return item_id
    
    def unregister_item(self, item_id: str) -> None:
        """
        Remove an item from the registry.
        
        Args:
            item_id: The ID of the item to remove
            
        Raises:
            ValueError: If the item ID is not found
        """
        if item_id not in self._registry_items:
            raise ValueError(f"Item '{item_id}' not found in registry")
        
        # Remove from registry
        del self._registry_items[item_id]
        
        # Remove from instance cache if present
        if item_id in self._instances:
            del self._instances[item_id]
        
        # Persist the changes
        self._save_registry()
    
    def _save_registry(self) -> None:
        """
        Save the registry to storage.
        
        By default, this saves to a JSON file. Subclasses can override
        this method for different storage mechanisms.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        
        try:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump({"items": list(self._registry_items.values())}, f, indent=2)
                
            logger.info(f"Saved registry with {len(self._registry_items)} items to {self.registry_path}")
        except Exception as e:
            logger.error(f"Error saving registry to {self.registry_path}: {str(e)}")
