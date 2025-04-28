"""
Provider Management Module

This module handles provider loading, initialization, and caching.
"""

import importlib
import logging
import os
from typing import Dict, Optional, Type

from . import Provider

logger = logging.getLogger(__name__)

# Module-level cache for provider instances
_provider_instances: Dict[str, Provider] = {}
_default_provider: Optional[Provider] = None

def _load_provider_class(provider_name: str) -> Optional[Type[Provider]]:
    """
    Dynamically load a provider class based on its name
    
    Args:
        provider_name: Name of the provider module (e.g. "azure", "dummy")
        
    Returns:
        Provider class or None if not found
    """
    try:
        # Try backend providers first
        try:
            module_name = f".backend.{provider_name.capitalize()}"
            module = importlib.import_module(module_name, package="OAIGateway.Providers")
        except ImportError:
            # Fall back to top-level providers
            module_name = f".{provider_name.capitalize()}"
            module = importlib.import_module(module_name, package="OAIGateway.Providers")
        
        # Find the provider class (assumes it follows naming convention)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Provider) and 
                attr is not Provider):
                return attr
                
        logger.error(f"No provider class found in module {module_name}")
        return None
        
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load provider {provider_name}: {e}")
        return None

def get_provider(provider_name: str) -> Optional[Provider]:
    """
    Get or initialize a provider instance by name
    
    Args:
        provider_name: Name of the provider (e.g. "azure")
        
    Returns:
        Provider instance or None if not found
    """
    global _provider_instances
    
    # Return cached instance if available
    if provider_name in _provider_instances:
        return _provider_instances[provider_name]
    
    # Load provider class
    provider_class = _load_provider_class(provider_name)
    if not provider_class:
        return None
    
    # Create and cache provider instance
    try:
        # Create an instance with default config based on provider
        if provider_name == "azure":
            provider_config = {
                "base_url": os.environ.get("AZUREOAI_URL", "http://127.0.0.1:9000")
            }
        elif provider_name == "dummy":
            provider_config = {
                "base_url": os.environ.get("DUMMY_URL", "http://dummy-provider")
            }
        else:
            # Generic config for other providers
            provider_config = {
                "base_url": os.environ.get(f"{provider_name.upper()}_URL", "http://127.0.0.1:9000")
            }
        
        provider = provider_class(provider_config)
        _provider_instances[provider_name] = provider
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize provider {provider_name}: {e}")
        return None

def get_default_provider() -> Optional[Provider]:
    """
    Get the default provider for the gateway
    
    Returns:
        Default provider instance or None if not available
    """
    global _default_provider
    
    # Return cached default provider if available
    if _default_provider is not None:
        return _default_provider
    
    # Use dummy provider as default for testing
    default_provider_name = os.environ.get("OAI_DEFAULT_PROVIDER", "dummy")
    _default_provider = get_provider(default_provider_name)
    
    return _default_provider

def get_provider_for_model(model: str) -> Optional[Provider]:
    """
    Determine and return the appropriate provider for a given model
    
    This is a placeholder for more sophisticated model-to-provider mapping.
    Currently, it just returns the default provider.
    
    Args:
        model: Model identifier string
        
    Returns:
        Provider instance or None if not available
    """
    # In the future, this could be based on model prefixes, configuration, etc.
    return get_default_provider()

def initialize_providers() -> None:
    """
    Pre-initialize all configured providers
    
    This can be called at application startup to eagerly load providers.
    """
    # Make sure default provider is initialized
    default_provider = get_default_provider()
    if default_provider:
        logger.info(f"Default provider initialized: {default_provider.get_provider_name()}")
    else:
        logger.warning("Failed to initialize default provider")
    
    # Could add logic here to initialize additional providers if needed