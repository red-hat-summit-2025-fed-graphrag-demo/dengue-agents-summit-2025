"""
Authentication Factory

This module provides a factory for creating authentication adapters
based on configuration and environment.
"""
import os
import logging
from typing import Dict, Any, Optional

from src.auth.constants import AuthProvider, DEFAULT_AUTH_CONFIG, KEYCLOAK_CONFIG
from src.auth.adapter.base import AuthAdapter

logger = logging.getLogger(__name__)


class AuthFactory:
    """
    Factory for creating authentication adapters.
    
    This class follows the singleton pattern to ensure consistent
    authentication configuration across the application.
    """
    _instance = None
    _adapter_instance = None
    _config = None
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(AuthFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the factory if not already initialized."""
        if self._initialized:
            return
            
        self._initialized = True
        self._adapter_instance = None
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load authentication configuration from environment variables or defaults.
        
        Returns:
            A dictionary containing auth configuration
        """
        config = DEFAULT_AUTH_CONFIG.copy()
        
        # Override with environment variables if available
        if os.environ.get("AUTH_PROVIDER"):
            provider_name = os.environ.get("AUTH_PROVIDER").upper()
            try:
                config["provider"] = AuthProvider[provider_name]
            except KeyError:
                logger.warning(f"Unknown AUTH_PROVIDER: {provider_name}, using default")
        
        # Load JWT-specific configuration
        if config["provider"] == AuthProvider.LOCAL_JWT:
            if os.environ.get("AUTH_SECRET_KEY"):
                config["secret_key"] = os.environ.get("AUTH_SECRET_KEY")
                
            if os.environ.get("AUTH_TOKEN_EXPIRY"):
                try:
                    config["token_expiry_seconds"] = int(os.environ.get("AUTH_TOKEN_EXPIRY"))
                except ValueError:
                    logger.warning("Invalid AUTH_TOKEN_EXPIRY, using default")
        
        # Load Keycloak-specific configuration
        elif config["provider"] == AuthProvider.KEYCLOAK:
            keycloak_config = KEYCLOAK_CONFIG.copy()
            
            if os.environ.get("KEYCLOAK_SERVER_URL"):
                keycloak_config["server_url"] = os.environ.get("KEYCLOAK_SERVER_URL")
                
            if os.environ.get("KEYCLOAK_REALM"):
                keycloak_config["realm"] = os.environ.get("KEYCLOAK_REALM")
                
            if os.environ.get("KEYCLOAK_CLIENT_ID"):
                keycloak_config["client_id"] = os.environ.get("KEYCLOAK_CLIENT_ID")
                
            if os.environ.get("KEYCLOAK_CLIENT_SECRET"):
                keycloak_config["client_secret"] = os.environ.get("KEYCLOAK_CLIENT_SECRET")
                
            if os.environ.get("KEYCLOAK_VERIFY_SSL"):
                keycloak_config["verify_ssl"] = os.environ.get("KEYCLOAK_VERIFY_SSL").lower() == "true"
                
            config["keycloak"] = keycloak_config
            
        return config
    
    def get_adapter(self) -> AuthAdapter:
        """
        Get the appropriate authentication adapter based on configuration.
        
        Returns:
            An instance of AuthAdapter
            
        Raises:
            ImportError: If the required adapter module is not available
            ValueError: If the adapter cannot be created
        """
        # Return cached adapter if available
        if self._adapter_instance is not None:
            return self._adapter_instance
            
        provider = self._config["provider"]
        
        if provider == AuthProvider.LOCAL_JWT:
            try:
                from src.auth.adapter.jwt_adapter import LocalJwtAuthAdapter
                self._adapter_instance = LocalJwtAuthAdapter(
                    secret_key=self._config["secret_key"],
                    token_expiry_seconds=self._config["token_expiry_seconds"],
                    issuer=self._config["issuer"]
                )
            except ImportError:
                logger.error("Failed to import LocalJwtAuthAdapter")
                raise ImportError("JWT authentication dependencies are not installed. "
                                "Run: pip install pyjwt cryptography")
                
        elif provider == AuthProvider.KEYCLOAK:
            try:
                from src.auth.adapter.keycloak_adapter import KeycloakAuthAdapter
                keycloak_config = self._config.get("keycloak", {})
                self._adapter_instance = KeycloakAuthAdapter(
                    server_url=keycloak_config.get("server_url"),
                    realm=keycloak_config.get("realm"),
                    client_id=keycloak_config.get("client_id"),
                    client_secret=keycloak_config.get("client_secret"),
                    verify_ssl=keycloak_config.get("verify_ssl", True)
                )
            except ImportError:
                logger.error("Failed to import KeycloakAuthAdapter")
                raise ImportError("Keycloak authentication dependencies are not installed. "
                                "Run: pip install python-keycloak")
        else:
            raise ValueError(f"Unsupported authentication provider: {provider}")
            
        return self._adapter_instance


# Convenience function to get the auth adapter
def get_auth_adapter() -> AuthAdapter:
    """
    Get the configured authentication adapter.
    
    This is a convenience function that creates an AuthFactory instance
    and returns the appropriate adapter.
    
    Returns:
        An instance of AuthAdapter
    """
    factory = AuthFactory()
    return factory.get_adapter()
