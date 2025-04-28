"""
A Dummy Backend Provider for testing

This provider returns canned responses without hitting an actual backend API.
It's useful for testing, development, and demonstrations.
"""

import logging
import time
from typing import Dict, Any
import uuid

from OAIGateway import OAIChatCompletionRequest, OAIChatCompletionResponse, OAIUsage, OAIChatMessage
from OAIGateway.Providers import Provider

logger = logging.getLogger(__name__)


class DummyProvider(Provider):
    """
    A dummy provider for testing that returns canned responses
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration
        
        Args:
            config: Dictionary with configuration values
        """
        self.config = config
        self.base_url = config.get("base_url", "http://dummy-provider")
        logger.info(f"Initialized Dummy provider with base URL: {self.base_url}")
    
    @classmethod
    def get_provider_name(cls) -> str:
        """Return the provider's unique identifier"""
        return "dummy"
    
    def get_backend_url(self) -> str:
        """Return the base URL for the backend service"""
        return self.base_url
    
    def get_backend_endpoint(self, request_type: str) -> str:
        """
        Return the appropriate backend endpoint for the request type
        
        Args:
            request_type: Type of request (e.g., "chat_completion", "embedding")
            
        Returns:
            Endpoint path for the specified request type
        """
        # Since this is a dummy provider, we don't actually use these endpoints
        endpoints = {
            "chat_completion": "/v1/chat/completions",
            "embeddings": "/v1/embeddings",
        }
        return endpoints.get(request_type, "/")
    
    def transform_chat_request(self, oai_request: OAIChatCompletionRequest) -> dict:
        """
        Transform OpenAI chat completion request to provider format
        
        For the dummy provider, we just pass through the request as-is
        since we don't actually call a backend.
        
        Args:
            oai_request: Validated OpenAI request object
            
        Returns:
            Provider-specific request payload as a dictionary
        """
        # Since this is a dummy provider, we just return the request as a dict
        return oai_request.dict()
    
    def transform_chat_response(
        self, 
        backend_response: dict, 
        original_request: OAIChatCompletionRequest
    ) -> OAIChatCompletionResponse:
        """
        Transform provider response to OpenAI chat completion format
        
        Since this is a dummy provider that doesn't actually call a backend,
        we generate our own mock response here.
        
        Args:
            backend_response: Provider response payload (unused in this case)
            original_request: Original OpenAI request for context
            
        Returns:
            OpenAI-compatible response object
        """
        # Extract the last user message to compose our dummy response
        user_messages = [msg for msg in original_request.messages if msg.role == "user"]
        last_user_message = user_messages[-1] if user_messages else None
        last_message_content = last_user_message.content if last_user_message else ""
        
        # Prepare a dummy response
        dummy_content = f"This is a dummy response to: '{last_message_content}'"
        
        # Simulate processing based on request parameters
        if original_request.temperature and original_request.temperature > 1.0:
            dummy_content += " [Note: High temperature detected, response would be more creative]"
        
        # Create the response object
        response = OAIChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            object="chat.completion",
            created=int(time.time()),
            model=original_request.model,
            choices=[{
                "index": 0,
                "message": OAIChatMessage(
                    role="assistant",
                    content=dummy_content
                ),
                "finish_reason": "stop"
            }],
            usage=OAIUsage(
                prompt_tokens=len(str(original_request.messages)) // 4,  # Rough estimation
                completion_tokens=len(dummy_content) // 4,  # Rough estimation
                total_tokens=len(str(original_request.messages) + dummy_content) // 4  # Rough estimation
            )
        )
        
        return response
    
    def validate_model_support(self, model: str) -> bool:
        """
        Check if this provider supports the requested model
        
        Args:
            model: Model identifier string
            
        Returns:
            True if supported, False otherwise
        """
        # The dummy provider supports all models
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the backend service
        
        Returns:
            Dictionary with health status information
        """
        return {
            "status": "ok",
            "message": "Dummy provider is always healthy",
            "latency_ms": 1  # Simulated latency
        }