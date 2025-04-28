"""Provider system for the OAI Gateway

This module defines the base Provider interface and registry for transforming
OpenAI API requests to various backend formats and vice versa.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Mapping

class Provider(ABC):
  """Base provider interface for request/response transformations"""

  @classmethod
  @abstractmethod
  def load_provider(cls, env: Mapping[str, str]) -> Provider:
    """Loads a Provider from an environment mapping"""
    
  @abstractmethod
  def get_backend_url(self) -> str:
    """Return the base URL for the Provider"""
    pass
  
  @abstractmethod
  def get_backend_endpoint(self, request_type: str) -> str:
    """
    Return the appropriate backend endpoint for the request type
    
    Args:
      request_type: Type of request (e.g., "chat_completion", "embedding")
      
    Returns:
      Endpoint path for the specified request type
    """
    pass
  
  @abstractmethod
  def transform_chat_request(self, oai_request: OAIChatCompletionRequest) -> dict:
    """
    Transform OpenAI chat completion request to provider format
    
    Args:
      oai_request: Validated OpenAI request object
      
    Returns:
      Provider-specific request payload as a dictionary
    """
    pass
  
  @abstractmethod
  def transform_chat_response(
    self, 
    backend_response: dict, 
    original_request: OAIChatCompletionRequest
  ) -> OAIChatCompletionResponse:
    """
    Transform provider response to OpenAI chat completion format
    
    Args:
      backend_response: Provider response payload
      original_request: Original OpenAI request for context
      
    Returns:
      OpenAI-compatible response object
    """
    pass
  
  def list_models(self, model: str) -> list[str]:
    """
    Lists the set of models available from the provicder by name
    
    Args:
      model: Model identifier string
      
    Returns:
      True if supported, False otherwise
    """
    pass
  
  def preprocess_headers(self, headers: dict) -> dict:
    """
    Prepare headers for forwarding to backend
    
    Args:
      headers: Original request headers
      
    Returns:
      Modified headers for backend request
    """
    # Default implementation - can be overridden
    return headers
  
  async def health_check(self) -> Dict[str, Any]:
    """
    Check the health of the backend service
    
    Returns:
      Dictionary with health status information
    """
    # Default implementation - providers should override this
    return {
      "status": "unknown",
      "message": "Health check not implemented for this provider"
    }