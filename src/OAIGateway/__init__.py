#!/usr/bin/env python3
"""
OpenAI API Gateway Proxy

This script implements a lightweight API gateway that:
1. Accepts HTTPS requests following OpenAI API structure
2. Transforms OpenAI format requests to backend format
3. Proxies requests to a local backend service
4. Transforms backend responses back to OpenAI format
5. Terminates TLS locally using provided cert and key files

Architecture:
- Ingress: HTTPS on port 443 (uvicorn with TLS)
- Routing: FastAPI routes for OpenAI API endpoints
- Transformation: Convert between OpenAI and backend formats
- Proxy: Forward requests to backend with httpx
- Egress: Return OpenAI-compatible responses

Configuration is loaded from environment variables with sensible defaults.
"""

import json
import logging
import os
import sys
import time
import uuid
from typing import Dict, List, Literal, Optional, Union, Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError, model_validator

logger = logging.getLogger(__package__ or __name__)
request_logger = logging.getLogger("request_tracer")

# ------------------- Pydantic Models -------------------

# OpenAI API Models
class OAIFunctionCall(BaseModel):
    """Represents a function call in an OpenAI message"""
    name: str
    arguments: str

class OAIChatToolCall(BaseModel):
    """Represents a tool call in an OpenAI chat response"""
    id: str
    type: Literal["function"]
    function: Dict[str, str]

class OAIChatMessage(BaseModel):
    """Represents a single message in the OpenAI chat format"""
    role: str  # system, user, assistant, tool, or function
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[OAIFunctionCall] = None  # Deprecated but included for compatibility
    tool_calls: Optional[List[OAIChatToolCall]] = None
    
    @model_validator(mode='after')
    def validate_message(self) -> 'OAIChatMessage':
        """Validate message structure based on role"""
        # Assistant messages need either content or tool_calls
        if self.role == "assistant" and self.content is None and not self.tool_calls and not self.function_call:
            raise ValueError("Assistant messages must have either content or tool_calls or function_call")
        
        # Function messages must have name
        if self.role == "function" and not self.name:
            raise ValueError("Function messages must have a name")
            
        return self

class FunctionObject(BaseModel):
    """Defines a function object for tool definitions"""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)

class OAIChatCompletionTool(BaseModel):
    """Defines a tool that the model may call"""
    type: Literal["function"]
    function: FunctionObject

class OAIChatCompletionRequest(BaseModel):
    """OpenAI chat completion request format"""
    model: str
    messages: List[OAIChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False  # Streaming not supported in current implementation
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[OAIChatCompletionTool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
    model_config = {
        "extra": "allow"  # Allow additional fields for future compatibility
    }

class ChatCompletionTokenLogprob(BaseModel):
    """Token log probability details"""
    token: str
    logprob: float
    bytes: Optional[List[int]] = None
    top_logprobs: Optional[List[Dict[str, Any]]] = None

class LogProbsInfo(BaseModel):
    """Log probability information in response"""
    content: Optional[List[ChatCompletionTokenLogprob]] = None
    
    model_config = {
        "extra": "allow"  # Allow additional fields for future compatibility
    }

class OAIChatChoice(BaseModel):
    """Represents a single choice in an OpenAI chat completion response"""
    index: int
    message: OAIChatMessage
    finish_reason: str  # stop, length, content_filter, tool_calls, etc.
    logprobs: Optional[LogProbsInfo] = None

class OAIUsage(BaseModel):
    """Token usage information in OpenAI format"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[Dict[str, int]] = None
    completion_tokens_details: Optional[Dict[str, int]] = None
    
    model_config = {
        "extra": "allow"  # Allow additional fields for future compatibility
    }

class OAIChatCompletionResponse(BaseModel):
    """OpenAI chat completion response format"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OAIChatChoice]
    usage: OAIUsage
    system_fingerprint: Optional[str] = None
    service_tier: Optional[str] = None
    
    model_config = {
        "extra": "allow"  # Allow additional fields for future compatibility
    }

class OAIErrorResponse(BaseModel):
    """OpenAI API error response format"""
    error: Dict[str, Any]

# Backend API Models
class BackendConversationRequest(BaseModel):
    """Backend conversation request format"""
    conversation: List[Dict[str, str]]
    temperature: Optional[float] = None
    model_id: Optional[str] = None
    max_tokens: Optional[int] = None

class BackendConversationResponse(BaseModel):
    """Backend conversation response format"""
    reply: str
    token_count: Dict[str, int]

# ------------------- Helper Functions -------------------

def create_oai_error(status_code: int, message: str, type: str = "invalid_request_error") -> JSONResponse:
    """Create an OpenAI-compatible error response"""
    return JSONResponse(
        status_code=status_code,
        content={"error": {
            "message": message,
            "type": type,
            "code": type,
            "param": None,
            "status": status_code
        }}
    )

def verify_tls_files():
    """Verify that the TLS certificate and key files exist"""
    cert_path = os.environ.get("CERT_PATH", "cert.pem")
    key_path = os.environ.get("KEY_PATH", "key.pem")
    
    if not os.path.isfile(cert_path):
        logger.error(f"TLS certificate file not found: {cert_path}")
        sys.exit(1)
    if not os.path.isfile(key_path):
        logger.error(f"TLS key file not found: {key_path}")
        sys.exit(1)
    logger.info(f"TLS certificate and key files verified")