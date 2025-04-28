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
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__package__ or __name__)

# ------------------- Pydantic Models -------------------

# OpenAI API Models
class OAIChatMessage(BaseModel):
    """Represents a single message in the OpenAI chat format"""
    role: str  # system, user, assistant, or function
    content: str
    name: Optional[str] = None

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

class OAIChatChoice(BaseModel):
    """Represents a single choice in an OpenAI chat completion response"""
    index: int
    message: OAIChatMessage
    finish_reason: str  # stop, length, etc.

class OAIUsage(BaseModel):
    """Token usage information in OpenAI format"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class OAIChatCompletionResponse(BaseModel):
    """OpenAI chat completion response format"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OAIChatChoice]
    usage: OAIUsage

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

# ------------------- Transformation Functions -------------------

def oai_to_backend(oai_request: OAIChatCompletionRequest) -> BackendConversationRequest:
    """
    Transform OpenAI API request to backend format
    
    This function converts the OpenAI "messages" format into the backend's
    expected "conversation" structure and maps relevant parameters.
    """
    try:
        # Convert messages format
        conversation = [
            {"role": msg.role, "content": msg.content}
            for msg in oai_request.messages
        ]
        
        # Map parameters
        return BackendConversationRequest(
            conversation=conversation,
            temperature=oai_request.temperature,
            model_id=oai_request.model,
            max_tokens=oai_request.max_tokens
        )
    except Exception as e:
        logger.error(f"Error transforming OpenAI request to backend format: {e}")
        raise ValueError(f"Failed to transform request: {str(e)}")

def backend_to_oai(
    backend_response: BackendConversationResponse, 
    model: str
) -> OAIChatCompletionResponse:
    """
    Transform backend response to OpenAI API format
    
    This function converts the backend's "reply" format into the OpenAI
    chat completion response structure, including generating appropriate
    IDs and timestamps.
    """
    try:
        # Extract token counts or use defaults if not properly formatted
        prompt_tokens = backend_response.token_count.get("prompt", 0)
        completion_tokens = backend_response.token_count.get("completion", 0)
        total_tokens = backend_response.token_count.get("total", prompt_tokens + completion_tokens)
        
        # Create response in OpenAI format
        return OAIChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            created=int(time.time()),
            model=model,
            choices=[
                OAIChatChoice(
                    index=0,
                    message=OAIChatMessage(
                        role="assistant",
                        content=backend_response.reply
                    ),
                    finish_reason="stop"
                )
            ],
            usage=OAIUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
        )
    except Exception as e:
        logger.error(f"Error transforming backend response to OpenAI format: {e}")
        raise ValueError(f"Failed to transform response: {str(e)}")

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
    if not os.path.isfile(CERT_PATH):
        logger.error(f"TLS certificate file not found: {CERT_PATH}")
        sys.exit(1)
    if not os.path.isfile(KEY_PATH):
        logger.error(f"TLS key file not found: {KEY_PATH}")
        sys.exit(1)
    logger.info(f"TLS certificate and key files verified")

# ------------------- FastAPI App -------------------

app = FastAPI(
    title="OpenAI API Gateway",
    description="A local gateway proxy that transforms OpenAI API requests to backend format",
    version="0.1.0"
)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Handle OpenAI chat completions endpoint
    
    This endpoint:
    1. Receives and validates an OpenAI-compatible request
    2. Transforms it to backend format
    3. Forwards it to the backend service
    4. Transforms the backend response to OpenAI format
    5. Returns the transformed response to the client
    """
    # Get the raw request headers to forward them
    headers = dict(request.headers.items())
    # Remove headers that shouldn't be forwarded
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Parse the request body
    try:
        body = await request.json()
        oai_request = OAIChatCompletionRequest(**body)
        
        if oai_request.stream:
            return create_oai_error(
                400, 
                "Streaming responses are not supported in this implementation"
            )
            
        logger.info(f"Processing chat completion request for model: {oai_request.model}")
    except ValidationError as e:
        logger.error(f"Invalid request format: {e}")
        return create_oai_error(400, f"Invalid request format: {str(e)}")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return create_oai_error(400, "Request body must be valid JSON")
    
    # Transform request
    try:
        backend_request = oai_to_backend(oai_request)
    except ValueError as e:
        logger.error(f"Request transformation failed: {e}")
        return create_oai_error(400, str(e))
    
    # Forward to backend
    try:
        logger.debug(f"Forwarding request to backend at: {AZUREOAI_URL}/conversation")
        async with httpx.AsyncClient() as client:
            backend_response = await client.post(
                f"{AZUREOAI_URL}/conversation",
                json=backend_request.dict(exclude_none=True),
                headers=headers,
                timeout=60.0  # Reasonable timeout
            )
            
            # Handle backend errors
            if backend_response.status_code != 200:
                logger.warning(f"Backend returned error: {backend_response.status_code}")
                # Try to parse as JSON, fall back to text
                try:
                    error_content = backend_response.json()
                    error_message = error_content.get("error", {}).get("message", str(error_content))
                except:
                    error_message = backend_response.text
                
                return create_oai_error(
                    backend_response.status_code, 
                    f"Backend error: {error_message}"
                )
            
            # Transform response
            try:
                backend_data = backend_response.json()
                backend_resp_obj = BackendConversationResponse(**backend_data)
                oai_response = backend_to_oai(backend_resp_obj, oai_request.model)
                logger.info(f"Successfully processed request to: {oai_request.model}")
                return oai_response
            except ValidationError as e:
                logger.error(f"Invalid backend response format: {e}")
                return create_oai_error(502, f"Invalid backend response format: {str(e)}")
            except ValueError as e:
                logger.error(f"Response transformation failed: {e}")
                return create_oai_error(502, str(e))
            
    except httpx.RequestError as exc:
        logger.error(f"Error communicating with backend: {exc}")
        return create_oai_error(
            502, 
            f"Error communicating with backend: {str(exc)}",
            "service_unavailable"
        )

@app.get("/v1/models")
async def list_models():
    """Minimal implementation of the models endpoint"""
    # Hardcoded minimal response
    return {
        "data": [
            {
                "id": "internal-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "organization"
            }
        ],
        "object": "list"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns status of the proxy and attempts to check backend health
    """
    # Check if backend is reachable
    try:
        async with httpx.AsyncClient() as client:
            backend_response = await client.get(
                f"{AZUREOAI_URL}/health",
                timeout=2.0
            )
            backend_status = "ok" if backend_response.status_code == 200 else "degraded"
    except:
        backend_status = "unreachable"
    
    return {
        "status": "ok",
        "backend": backend_status,
        "timestamp": time.time()
    }

# ------------------- Middleware -------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their processing time"""
    start_time = time.time()
    path = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        status_code = response.status_code
        
        if 200 <= status_code < 300:
            log_level = logging.INFO
        elif 400 <= status_code < 500:
            log_level = logging.WARNING
        else:
            log_level = logging.ERROR
            
        logger.log(
            log_level,
            f"{method} {path} - Status: {status_code} - Time: {process_time:.4f}s"
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"{method} {path} - Exception: {str(e)} - Time: {process_time:.4f}s")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Internal server error", "type": "server_error"}}
        )
