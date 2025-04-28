"""

Implements `/chat/completions` OpenAI Endpoint.



"""

from . import app
import pydantic

@app.post('/chat/completions')
async def chat_completions(*args, **kwds):
  """Transforms an OpenAI ChatCompletion to an Azure AI Chat Completion"""

  """NOTE
  
  The primary difference between the 2 API services is

  A) AzureOAI has per model deployment api endpoints
  B) AzureOAI doesn't allow overriding model in the request body

  Otherwise they are practically identical
  
  """