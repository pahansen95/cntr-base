"""
Implements `/chat/completions` OpenAI Endpoint.

This module transforms the OpenAI ChatCompletion API format to Azure OpenAI format.
"""

from . import app
import pydantic
from typing import Dict, List, Optional, Union, Any, Literal
from fastapi import Body, HTTPException, Request, Depends
import httpx
import os
import json

# Pydantic models for request validation

class ChatCompletionMessage(pydantic.BaseModel):
  role: str
  content: Optional[Union[str, List[Dict[str, Any]]]] = None
  name: Optional[str] = None
  function_call: Optional[Dict[str, str]] = None
  tool_calls: Optional[List[Dict[str, Any]]] = None

class ChatCompletionRequest(pydantic.BaseModel):
  model: str
  messages: List[ChatCompletionMessage]
  temperature: Optional[float] = 1.0
  top_p: Optional[float] = 1.0
  n: Optional[int] = 1
  stream: Optional[bool] = False
  stop: Optional[Union[str, List[str]]] = None
  max_tokens: Optional[int] = None
  presence_penalty: Optional[float] = 0.0
  frequency_penalty: Optional[float] = 0.0
  logit_bias: Optional[Dict[str, float]] = None
  user: Optional[str] = None
  functions: Optional[List[Dict[str, Any]]] = None
  function_call: Optional[Union[str, Dict[str, str]]] = None
  tools: Optional[List[Dict[str, Any]]] = None
  tool_choice: Optional[Union[str, Dict[str, Any]]] = None
  response_format: Optional[Dict[str, str]] = None
  seed: Optional[int] = None
  logprobs: Optional[bool] = None
  top_logprobs: Optional[int] = None

# Configuration for Azure API access
class AzureConfig:
  def __init__(self):
    self.api_base = os.environ.get("AZURE_OPENAI_API_BASE", "https://your-resource-name.openai.azure.com")
    self.api_key = os.environ.get("AZURE_OPENAI_API_KEY", "your-api-key")
    self.api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
    
    # Model deployment mapping (OpenAI model ID -> Azure deployment name)
    self.deployment_map = {
      "gpt-4o": "gpt-4o",
      "gpt-4.1": "gpt-4.1",
      "gpt-4.1-mini": "gpt-4.1-mini",
      "gpt-4.1-nano": "gpt-4.1-nano",
      "o3": "o3",
      "o4-mini": "o4-mini",
    }

# Initialize Azure configuration
azure_config = AzureConfig()

async def get_azure_client():
  return httpx.AsyncClient(
    base_url=azure_config.api_base,
    headers={
      "api-key": azure_config.api_key,
      "Content-Type": "application/json"
    },
    timeout=180.0  # 3 minute timeout 
  )

@app.post('/chat/completions')
async def chat_completions(
  request: Request,
  azure_client: httpx.AsyncClient = Depends(get_azure_client)
):
  """Transforms an OpenAI ChatCompletion to an Azure AI Chat Completion"""
  try:
    # Parse the request body
    body = await request.json()
    oai_request = ChatCompletionRequest(**body)
    
    # Get the Azure deployment name for the requested model
    model = oai_request.model
    deployment_name = azure_config.deployment_map.get(model)
    
    if not deployment_name:
      raise HTTPException(
        status_code=400, 
        detail=f"Model '{model}' is not supported or mapped to an Azure deployment"
      )
    
    # Transform to Azure API format
    azure_request = {
      # Remove 'model' from the request as Azure doesn't accept it
      "messages": [msg.model_dump(exclude_none=True) for msg in oai_request.messages],
    }
    
    # Copy all the other parameters that are shared between APIs
    for field in [
      "temperature", "top_p", "n", "stream", "stop", "max_tokens",
      "presence_penalty", "frequency_penalty", "logit_bias", "user",
      "functions", "function_call", "tools", "tool_choice", 
      "response_format", "seed", "logprobs", "top_logprobs"
    ]:
      value = getattr(oai_request, field)
      if value is not None:
        azure_request[field] = value
    
    # Make the request to Azure OpenAI
    endpoint = f"/openai/deployments/{deployment_name}/chat/completions?api-version={azure_config.api_version}"
    azure_response = await azure_client.post(
      endpoint,
      json=azure_request
    )
    
    # Check for errors
    if azure_response.status_code != 200:
      error_detail = azure_response.json() if azure_response.headers.get("content-type") == "application/json" else azure_response.text
      raise HTTPException(
        status_code=azure_response.status_code,
        detail=f"Azure OpenAI API error: {error_detail}"
      )
    
    # For streaming responses, we need to stream the response back
    if oai_request.stream:
      return azure_response.aiter_raw()
    
    # For non-streaming, just return the JSON response
    # The response format is already compatible with OpenAI format
    return azure_response.json()
    
  except pydantic.ValidationError as e:
    raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")