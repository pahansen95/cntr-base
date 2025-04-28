"""Provider system for the OAI Gateway

This module defines the base Provider interface and registry for transforming
OpenAI API requests to various backend formats and vice versa.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

from OAIGateway import OAIChatCompletionRequest, OAIChatCompletionResponse


class Provider(ABC):
    """Base provider interface for request/response transformations"""
    
    @classmethod
    @abstractmethod
    def get_provider_name(cls) -> str:
        """Return the provider's unique identifier"""
        pass
    
    @abstractmethod
    def get_backend_url(self) -> str:
        """Return the base URL for the backend service"""
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
    
    def validate_model_support(self, model: str) -> bool:
        """
        Check if this provider supports the requested model
        
        Args:
            model: Model identifier string
            
        Returns:
            True if supported, False otherwise
        """
        # Default implementation - can be overridden
        return True
    
    def preprocess_headers(self, headers: dict) -> dict:
        """
        Prepare headers for forwarding to backend
        
        Args:
            headers: Original request headers
            
        Returns:
            Modified headers for backend request
        """
        # Default implementation - can be overridden
        processed = headers.copy()
        processed.pop("host", None)
        processed.pop("content-length", None)
        return processed
    
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