"""

Implements `/chat/completions` OpenAI Endpoint

"""

from . import app
import pydantic

@app.post('/chat/completions')
async def chat_completions(*args, **kwds): ...