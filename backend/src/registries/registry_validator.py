"""
Registry Validator

Provides validation logic for registry entries to ensure they comply
with the standardized format defined in REGISTRY_STANDARD.md.
"""
import logging
from typing import Dict, List, Optional, Any, Set, Callable, Union
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "ERROR"          # Required field missing or invalid format
    WARNING = "WARNING"      # Recommended field missing or potential issue
    INFO = "INFO"            # Optional field missing or informational message

class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.is_valid: bool = True
    
    def add_issue(self, field: str, message: str, severity: ValidationSeverity) -> None:
        """
        Add a validation issue.
        
        Args:
            field: The field with the issue
            message: Description of the issue
            severity: Severity level of the issue
        """
        self.issues.append({
            "field": field,
            "message": message,
            "severity": severity
        })
        
        # Only mark as invalid for ERROR severity
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False
    
    def get_formatted_issues(self) -> List[str]:
        """
        Get a list of formatted issue messages.
        
        Returns:
            List of formatted issue messages
        """
        return [
            f"[{issue['severity'].value}] {issue['field']}: {issue['message']}"
            for issue in self.issues
        ]
    
    def __str__(self) -> str:
        """String representation of validation results."""
        if not self.issues:
            return "Validation passed with no issues."
        
        status = "passed" if self.is_valid else "failed"
        issues = "\n".join(self.get_formatted_issues())
        return f"Validation {status} with {len(self.issues)} issues:\n{issues}"

class RegistryValidator:
    """
    Base validator for registry entries.
    
    Provides common validation logic for all registry types.
    """
    
    # Common required fields across all registry types
    COMMON_REQUIRED_FIELDS = {
        "id": str,
        "name": str,
        "description": str,
        "active": bool
    }
    
    # Common optional fields across all registry types
    COMMON_OPTIONAL_FIELDS = {
        "version": str,
        "tags": list,
        "created_at": str,
        "updated_at": str,
        "author": str
    }
    
    def __init__(self, required_fields: Optional[Dict[str, type]] = None, 
                 optional_fields: Optional[Dict[str, type]] = None):
        """
        Initialize the validator.
        
        Args:
            required_fields: Additional required fields specific to this validator
            optional_fields: Additional optional fields specific to this validator
        """
        # Combine common fields with specific fields
        self.required_fields = dict(self.COMMON_REQUIRED_FIELDS)
        if required_fields:
            self.required_fields.update(required_fields)
            
        self.optional_fields = dict(self.COMMON_OPTIONAL_FIELDS)
        if optional_fields:
            self.optional_fields.update(optional_fields)
    
    def validate(self, item: Dict[str, Any]) -> ValidationResult:
        """
        Validate a registry item against the required schema.
        
        Args:
            item: The registry item to validate
            
        Returns:
            ValidationResult with validation findings
        """
        result = ValidationResult()
        
        # Validate required fields
        for field_name, field_type in self.required_fields.items():
            if field_name not in item:
                result.add_issue(
                    field=field_name,
                    message=f"Required field '{field_name}' is missing",
                    severity=ValidationSeverity.ERROR
                )
                continue
                
            if not isinstance(item[field_name], field_type):
                result.add_issue(
                    field=field_name,
                    message=f"Field '{field_name}' should be of type {field_type.__name__}, " \
                           f"got {type(item[field_name]).__name__}",
                    severity=ValidationSeverity.ERROR
                )
        
        # Validate optional fields (if present)
        for field_name, field_type in self.optional_fields.items():
            if field_name in item and not isinstance(item[field_name], field_type):
                result.add_issue(
                    field=field_name,
                    message=f"Field '{field_name}' should be of type {field_type.__name__}, " \
                           f"got {type(item[field_name]).__name__}",
                    severity=ValidationSeverity.WARNING
                )
        
        # Check for recommended but not required fields
        for field_name in self.optional_fields:
            if field_name not in item:
                result.add_issue(
                    field=field_name,
                    message=f"Recommended field '{field_name}' is missing",
                    severity=ValidationSeverity.INFO
                )
        
        # Validate version format
        if "version" in item and isinstance(item["version"], str):
            self._validate_version_format(item["version"], result)
        
        # Validate dates format
        for date_field in ["created_at", "updated_at"]:
            if date_field in item and isinstance(item[date_field], str):
                self._validate_date_format(date_field, item[date_field], result)
        
        return result
    
    def _validate_version_format(self, version: str, result: ValidationResult) -> None:
        """
        Validate that the version field follows semantic versioning.
        
        Args:
            version: The version string to validate
            result: ValidationResult to add issues to
        """
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            result.add_issue(
                field="version",
                message=f"Version '{version}' does not follow semantic versioning (X.Y.Z)",
                severity=ValidationSeverity.WARNING
            )
    
    def _validate_date_format(self, field_name: str, date_str: str, result: ValidationResult) -> None:
        """
        Validate that a date field follows ISO format (YYYY-MM-DD).
        
        Args:
            field_name: Name of the date field
            date_str: The date string to validate
            result: ValidationResult to add issues to
        """
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            result.add_issue(
                field=field_name,
                message=f"Date '{date_str}' does not follow ISO format (YYYY-MM-DD)",
                severity=ValidationSeverity.WARNING
            )

class ToolRegistryValidator(RegistryValidator):
    """Validator for tool registry entries."""
    
    def __init__(self):
        """Initialize the tool registry validator with tool-specific fields."""
        super().__init__(
            required_fields={
                "module_path": str,
                "class_name": str,
                "config_path": str,
                "allowed_agents": list
            },
            optional_fields={
                "type": str
            }
        )
    
    def validate(self, item: Dict[str, Any]) -> ValidationResult:
        """
        Validate a tool registry item.
        
        Args:
            item: The tool registry item to validate
            
        Returns:
            ValidationResult with validation findings
        """
        result = super().validate(item)
        
        # Additional tool-specific validations
        if "allowed_agents" in item and isinstance(item["allowed_agents"], list):
            if len(item["allowed_agents"]) == 0:
                result.add_issue(
                    field="allowed_agents",
                    message="Empty allowed_agents list means this tool cannot be used by any agent",
                    severity=ValidationSeverity.WARNING
                )
        
        return result

class AgentRegistryValidator(RegistryValidator):
    """Validator for agent registry entries."""
    
    def __init__(self):
        """Initialize the agent registry validator with agent-specific fields."""
        super().__init__(
            required_fields={
                "module_path": str,
                "class_name": str,
                "config_path": str,
                "prompt_id": str,
                "model_config": dict
            },
            optional_fields={
                "tools": list,
                "allowed_workflows": list
            }
        )
    
    def validate(self, item: Dict[str, Any]) -> ValidationResult:
        """
        Validate an agent registry item.
        
        Args:
            item: The agent registry item to validate
            
        Returns:
            ValidationResult with validation findings
        """
        result = super().validate(item)
        
        # Validate model_config fields
        if "model_config" in item and isinstance(item["model_config"], dict):
            model_config = item["model_config"]
            
            # Required model_config fields
            for field in ["model_type", "max_tokens", "temperature"]:
                if field not in model_config:
                    result.add_issue(
                        field=f"model_config.{field}",
                        message=f"Required field '{field}' missing in model_config",
                        severity=ValidationSeverity.ERROR
                    )
            
            # Validate numeric fields
            for field in ["max_tokens", "temperature", "top_p"]:
                if field in model_config and not isinstance(model_config[field], (int, float)):
                    result.add_issue(
                        field=f"model_config.{field}",
                        message=f"Field '{field}' in model_config should be a number",
                        severity=ValidationSeverity.ERROR
                    )
        
        return result

class PromptRegistryValidator(RegistryValidator):
    """Validator for prompt registry entries."""
    
    def __init__(self):
        """Initialize the prompt registry validator with prompt-specific fields."""
        super().__init__(
            required_fields={
                "prompt": str
            },
            optional_fields={
                "models": list
            }
        )
    
    def validate(self, item: Dict[str, Any]) -> ValidationResult:
        """
        Validate a prompt registry item.
        
        Args:
            item: The prompt registry item to validate
            
        Returns:
            ValidationResult with validation findings
        """
        result = super().validate(item)
        
        # Additional prompt-specific validations
        if "prompt" in item and isinstance(item["prompt"], str):
            if len(item["prompt"]) < 10:
                result.add_issue(
                    field="prompt",
                    message="Prompt text is suspiciously short (less than 10 characters)",
                    severity=ValidationSeverity.WARNING
                )
        
        return result

def get_validator_for_registry_type(registry_type: str) -> RegistryValidator:
    """
    Get the appropriate validator for a registry type.
    
    Args:
        registry_type: Type of registry ('tool', 'agent', 'prompt')
        
    Returns:
        Appropriate RegistryValidator instance
        
    Raises:
        ValueError: If registry_type is not recognized
    """
    validators = {
        "tool": ToolRegistryValidator(),
        "agent": AgentRegistryValidator(),
        "prompt": PromptRegistryValidator()
    }
    
    if registry_type not in validators:
        raise ValueError(f"Unknown registry type: {registry_type}")
    
    return validators[registry_type]
