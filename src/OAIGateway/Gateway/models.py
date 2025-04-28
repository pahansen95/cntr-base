"""
Implements `/models` OpenAI Endpoint.

This module implements the models endpoint to list available models.
"""

from . import app, logger
import pydantic
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
import logging

# Pydantic models for response validation
class Model(pydantic.BaseModel):
  id: str
  object: str = "model"
  created: int
  owned_by: str

class ListModelsResponse(pydantic.BaseModel):
  object: str = "list"
  data: List[Model]

# Hardcoded list of models
# Based on the Azure deployment mapping in chat_completions.py
AVAILABLE_MODELS: list[Model] = [
  Model(**{
    "id": name,
    "object": "model",
    "created": 0, # 
    "owned_by": "openai"
  }) for name in {
    'gpt-4o',
    'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano',
    'o3', 'o4-mini',
  }
]

@app.get('/models')
async def list_models():
  """Returns a list of available models"""
  logger.debug("Received models list request")
  
  try:
    # Create the response using our hardcoded models
    response = ListModelsResponse(
      data=AVAILABLE_MODELS.copy()
    )
    
    logger.debug(f"Returning {len(response.data)} models")
    return response.model_dump()
    
  except Exception as e:
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")