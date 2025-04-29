"""
Implements `/chat/completions` OpenAI Endpoint.

This module transforms the OpenAI ChatCompletion API format to Azure OpenAI format.
"""

from . import app, logger
import pydantic
from typing import Dict, List, Optional, Union, Any, Literal
from fastapi import Body, HTTPException, Request, Depends
import fastapi.responses
import httpx
import os
import json
import logging

# Pydantic models for request validation

class ContentPartText(pydantic.BaseModel):
  type: Literal["text"]
  text: str

class ContentPartImageUrl(pydantic.BaseModel):
  url: str
  detail: Optional[Literal["auto", "low", "high"]] = "auto"

class ContentPartImage(pydantic.BaseModel):
  type: Literal["image_url"]
  image_url: ContentPartImageUrl

class ContentPartRefusal(pydantic.BaseModel):
  type: Literal["refusal"]
  refusal: str

class ContentPartAudio(pydantic.BaseModel):
  type: Literal["input_audio"]
  input_audio: Dict[str, Any]

class ContentPartFile(pydantic.BaseModel):
  type: Literal["file"]
  file: Dict[str, Any]

class FunctionObject(pydantic.BaseModel):
  name: str
  description: Optional[str] = None
  parameters: Optional[Dict[str, Any]] = None
  strict: Optional[bool] = False

class ChatCompletionTool(pydantic.BaseModel):
  type: Literal["function"]
  function: FunctionObject

class ChatCompletionNamedToolChoice(pydantic.BaseModel):
  type: Literal["function"]
  function: Dict[str, str]

class ChatCompletionToolCall(pydantic.BaseModel):
  id: str
  type: Literal["function"]
  function: Dict[str, str]

class ChatCompletionMessageToolCall(pydantic.BaseModel):
  id: str
  type: Literal["function"]
  function: Dict[str, str]

class ChatCompletionMessageBase(pydantic.BaseModel):
  role: str
  name: Optional[str] = None

class ChatCompletionMessageSystem(ChatCompletionMessageBase):
  role: Literal["system"]
  content: Union[str, List[ContentPartText]]

class ChatCompletionMessageDeveloper(ChatCompletionMessageBase):
  role: Literal["developer"]
  content: Union[str, List[ContentPartText]]

class ChatCompletionMessageUser(ChatCompletionMessageBase):
  role: Literal["user"]
  content: Union[str, List[Union[ContentPartText, ContentPartImage, ContentPartAudio, ContentPartFile]]]

class ChatCompletionMessageAssistant(ChatCompletionMessageBase):
  role: Literal["assistant"]
  content: Optional[Union[str, List[Union[ContentPartText, ContentPartRefusal]]]] = None
  function_call: Optional[Dict[str, str]] = None
  tool_calls: Optional[List[ChatCompletionToolCall]] = None
  refusal: Optional[str] = None
  audio: Optional[Dict[str, Any]] = None

class ChatCompletionMessageTool(ChatCompletionMessageBase):
  role: Literal["tool"]
  content: Union[str, List[ContentPartText]]
  tool_call_id: str

class ChatCompletionMessageFunction(ChatCompletionMessageBase):
  role: Literal["function"]
  content: str
  name: str

class ChatCompletionMessage(pydantic.BaseModel):
  role: str
  content: Optional[Union[str, List[Dict[str, Any]]]] = None
  name: Optional[str] = None
  function_call: Optional[Dict[str, str]] = None
  tool_calls: Optional[List[Dict[str, Any]]] = None
  tool_call_id: Optional[str] = None
  refusal: Optional[str] = None
  audio: Optional[Dict[str, Any]] = None

class ResponseFormatType(pydantic.BaseModel):
  type: str

class ResponseFormatText(ResponseFormatType):
  type: Literal["text"]

class ResponseFormatJsonSchema(ResponseFormatType):
  type: Literal["json_schema"]
  json_schema: Dict[str, Any]

class ResponseFormatJsonObject(ResponseFormatType):
  type: Literal["json_object"]

class ChatCompletionRequest(pydantic.BaseModel):
  model: str
  messages: List[ChatCompletionMessage]
  temperature: Optional[float] = 1.0
  top_p: Optional[float] = 1.0
  n: Optional[int] = 1
  stream: Optional[bool] = False
  stop: Optional[Union[str, List[str]]] = None
  max_tokens: Optional[int] = None
  max_completion_tokens: Optional[int] = None
  presence_penalty: Optional[float] = 0.0
  frequency_penalty: Optional[float] = 0.0
  logit_bias: Optional[Dict[str, float]] = None
  user: Optional[str] = None
  functions: Optional[List[Dict[str, Any]]] = None
  function_call: Optional[Union[str, Dict[str, str]]] = None
  tools: Optional[List[ChatCompletionTool]] = None
  tool_choice: Optional[Union[Literal["none", "auto", "required"], ChatCompletionNamedToolChoice]] = None
  response_format: Optional[Union[ResponseFormatText, ResponseFormatJsonSchema, ResponseFormatJsonObject]] = None
  seed: Optional[int] = None
  logprobs: Optional[bool] = None
  top_logprobs: Optional[int] = None
  stream_options: Optional[Dict[str, Any]] = None
  parallel_tool_calls: Optional[bool] = None
  reasoning_effort: Optional[Literal["low", "medium", "high"]] = None
  modalities: Optional[List[Literal["text", "audio"]]] = None
  store: Optional[bool] = False
  service_tier: Optional[Literal["auto", "default"]] = "auto"
  web_search_options: Optional[Dict[str, Any]] = None
  audio: Optional[Dict[str, Any]] = None
  prediction: Optional[Dict[str, Any]] = None
  metadata: Optional[Dict[str, str]] = None

# Configuration for Azure API access
class AzureConfig:
  def __init__(self):
    self.api_base = os.environ["AZURE_OPENAI_API_BASE"]
    self.api_key = os.environ["AZURE_OPENAI_API_KEY"]
    self.api_version = os.environ["AZURE_OPENAI_API_VERSION"]
    
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
  logger.debug(f"Received chat completion request")
  try:
    # Parse the request body
    body = await request.json()
    logger.debug(f"Request body: {body}")
    oai_request = ChatCompletionRequest(**body)
    
    # Validate tool_call_id references
    messages = oai_request.messages
    for i, msg in enumerate(messages):
      if i > 0 and msg.role == "tool" and msg.tool_call_id:
        prev_msg = messages[i-1]
        # Check if previous message has tool_calls
        if prev_msg.role != "assistant" or not prev_msg.tool_calls:
          raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: 'tool_call_id' of '{msg.tool_call_id}' not found in 'tool_calls' of previous message (previous message has no tool_calls)"
          )
        
        # Check if tool_call_id exists in previous message's tool_calls
        tool_call_ids = [tool_call.get("id") for tool_call in prev_msg.tool_calls]
        if msg.tool_call_id not in tool_call_ids:
          raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: 'tool_call_id' of '{msg.tool_call_id}' not found in 'tool_calls' of previous message"
          )
    
    # Get the Azure deployment name for the requested model
    model = oai_request.model
    logger.debug(f"Requested model: {model}")
    deployment_name = azure_config.deployment_map.get(model)
    logger.debug(f"Mapped to deployment: {deployment_name}")
    
    if not deployment_name:
      logger.warning(f"Model '{model}' not found in deployment map")
      raise HTTPException(
        status_code=400, 
        detail=f"Model '{model}' is not supported or mapped to an Azure deployment"
      )
    
    # Validate tool messages have valid tool_call_id references
    messages = oai_request.messages
    for i, msg in enumerate(messages):
      if msg.role == "tool" and msg.tool_call_id:
        if i == 0:
          raise HTTPException(
            status_code=400,
            detail=f"Tool message cannot be the first message in the conversation"
          )
        
        prev_msg = messages[i-1]
        if prev_msg.role != "assistant":
          raise HTTPException(
            status_code=400,
            detail=f"Tool message must follow an assistant message"
          )
        
        if not prev_msg.tool_calls:
          raise HTTPException(
            status_code=400,
            detail=f"Tool message references tool_call_id '{msg.tool_call_id}', but previous assistant message has no tool_calls"
          )
        
        # Extract tool call IDs from previous message
        tool_call_ids = [tool_call.get("id") for tool_call in prev_msg.tool_calls]
        if msg.tool_call_id not in tool_call_ids:
          raise HTTPException(
            status_code=400,
            detail=f"Invalid tool_call_id '{msg.tool_call_id}': not found in previous message's tool_calls: {tool_call_ids}"
          )
    
    # Transform to Azure API format
    azure_request = {
      # Remove 'model' from the request as Azure doesn't accept it
      "messages": [msg.model_dump(exclude_none=True) for msg in oai_request.messages],
    }
    
    # Helper function to make complex objects JSON serializable
    def prepare_for_json(obj):
      if hasattr(obj, 'model_dump'):
        return obj.model_dump(exclude_none=True)
      elif isinstance(obj, list):
        return [prepare_for_json(item) for item in obj]
      elif isinstance(obj, dict):
        return {k: prepare_for_json(v) for k, v in obj.items()}
      else:
        return obj
    
    # Copy all the other parameters that are shared between APIs
    for field in [
      "temperature", "top_p", "n", "stream", "stop", "max_tokens", "max_completion_tokens",
      "presence_penalty", "frequency_penalty", "logit_bias", "user",
      "functions", "function_call", "response_format", "seed", "logprobs", "top_logprobs",
      "stream_options", "parallel_tool_calls"
    ]:
      value = getattr(oai_request, field)
      if value is not None:
        azure_request[field] = prepare_for_json(value)
    
    # Handle tools and tool_choice separately as they require serialization
    if oai_request.tools is not None:
      azure_request["tools"] = prepare_for_json(oai_request.tools)
      
    if oai_request.tool_choice is not None:
      azure_request["tool_choice"] = prepare_for_json(oai_request.tool_choice)
    
    # Make the request to Azure OpenAI
    endpoint = f"/openai/deployments/{deployment_name}/chat/completions?api-version={azure_config.api_version}"
    logger.debug(f"Sending request to Azure endpoint: {endpoint}")
    logger.debug(f"Azure request payload: {azure_request}")
    azure_response = await azure_client.post(
      endpoint,
      json=azure_request
    )
    logger.debug(f"Azure response status: {azure_response.status_code}")
    
    # Check for errors
    if azure_response.status_code != 200:
      error_detail = azure_response.json() if azure_response.headers.get("content-type") == "application/json" else azure_response.text
      raise HTTPException(
        status_code=azure_response.status_code,
        detail=f"Azure OpenAI API error: {error_detail}"
      )
    
    # For streaming responses, we need to stream the response back
    if oai_request.stream:
      logger.debug("Returning streaming response")
      
      async def stream_generator():
        async for chunk in azure_response.aiter_bytes():
          yield chunk
          
      return fastapi.responses.StreamingResponse(
        stream_generator(),
        media_type="application/json"
      )
    
    # For non-streaming, just return the JSON response
    # The response format is already compatible with OpenAI format
    logger.debug(f"Returning JSON response")
    return azure_response.json()
    
  except pydantic.ValidationError as e:
    logger.error(f"Validation error: {str(e)}")
    raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
  
  except Exception as e:
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")