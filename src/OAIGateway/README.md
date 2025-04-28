# OpenAI API Gateway Proxy

A lightweight, single-file API gateway that transforms OpenAI API requests into a custom backend format and provides local TLS termination.

## Features

- Accepts HTTPS requests following OpenAI API structure
- Transforms request payloads between OpenAI and backend formats
- Translates endpoint paths
- Proxies requests to a local backend service
- Transforms backend responses back to OpenAI format
- Terminates TLS locally with provided certificates
- Comprehensive error handling and logging
- Configuration via environment variables

## Requirements

- Python 3.12+
- FastAPI
- Uvicorn (with standard extras for TLS support)
- httpx
- Pydantic

## Installation

```bash
pip install fastapi uvicorn[standard] httpx pydantic
```

Alternatively, use the provided requirements.txt:

```bash
pip install -r requirements.txt
```

## Configuration

The gateway can be configured using environment variables:

| Environment Variable | Description | Default Value |
|----------------------|-------------|---------------|
| `AZUREOAI_URL` | URL of your backend service | `http://127.0.0.1:9000` |
| `CERT_PATH` | Path to SSL certificate | `cert.pem` |
| `KEY_PATH` | Path to SSL key | `key.pem` |
| `LISTEN_HOST` | Host to listen on | `0.0.0.0` |
| `LISTEN_PORT` | Port to listen on | `443` |
| `LOG_LEVEL` | Logging level | `INFO` |

You can set these variables in your shell before running the script, or use a `.env` file with a tool like `python-dotenv` to load them.

## TLS Certificate Setup

For local development, you can generate a self-signed certificate:

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
```

## Running the Gateway

The gateway requires elevated privileges to bind to port 443:

```bash
sudo python gateway.py
```

## Endpoints

- `/v1/chat/completions`: Handles chat completion requests in OpenAI format
- `/v1/models`: Returns a simple list of available models
- `/health`: Health check endpoint

## Request/Response Flow

1. Client sends an OpenAI-formatted request to the gateway
2. Gateway validates and transforms the request to backend format
3. Gateway forwards the transformed request to the backend
4. Backend processes the request and returns a response
5. Gateway transforms the backend response to OpenAI format
6. Gateway returns the OpenAI-formatted response to the client

## Request Transformation

The gateway transforms OpenAI's "messages" format:

```json
{
  "model": "model-id",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7
}
```

Into the backend's "conversation" format:

```json
{
  "conversation": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "model_id": "model-id"
}
```

## Response Transformation

Similarly, the backend's response:

```json
{
  "reply": "Hi there! How can I assist you today?",
  "token_count": {
    "prompt": 20,
    "completion": 10,
    "total": 30
  }
}
```

Is transformed back to OpenAI format:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1682031648,
  "model": "model-id",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hi there! How can I assist you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

## Limitations

- Streaming responses are not supported
- Limited to hardcoded endpoints
- No authentication handling
- Self-signed certificates for development only

## Troubleshooting

- **Gateway fails to start**: Ensure the certificate and key files exist and are valid
- **Connection refused**: Verify the backend service is running at the configured URL
- **SSL errors**: Check that your client trusts the self-signed certificate
- **Request errors**: Examine the logs for details on request validation or transformation issues

## Security Considerations

This gateway is intended for local development only. For production use, consider:

- Using proper certificates from a trusted CA
- Implementing authentication and authorization
- Adding rate limiting
- Containerizing the application
- Configuring through environment variables instead of hardcoding