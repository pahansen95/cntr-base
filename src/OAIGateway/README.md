# OpenAI API Gateway Proxy

A modular API gateway that transforms OpenAI API requests into provider-specific formats and provides local TLS termination.

## Features

- Accepts HTTPS requests following OpenAI API structure
- Transforms request payloads between OpenAI and backend formats
- Extensible provider system for different backend services
- Proxies requests to configured backend services
- Transforms backend responses back to OpenAI format
- Terminates TLS locally with provided certificates
- Comprehensive error handling and logging
- Configuration via environment variables

## Project Structure

```
OAIGateway/
├── __init__.py         # Core models and utilities
├── __main__.py         # Entry point for running as a module
├── gateway.py          # FastAPI routes and request handling
├── Providers/          # Provider implementations
│   ├── __init__.py     # Base Provider interface
│   ├── backend/        # Backend provider implementations
│   │   ├── __init__.py # Backend provider utilities
│   │   ├── Azure.py    # Azure OpenAI provider implementation
│   │   └── Dummy.py    # Dummy provider for testing
│   └── manager.py      # Provider loading and management
├── requirements.txt    # Dependencies
└── certs.sh            # TLS certificate generation script
```

## Requirements

- Python 3.12+
- FastAPI
- Uvicorn (with standard extras for TLS support)
- httpx
- Pydantic
- uuid

## Installation

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
| `LISTEN_HOST` | Host to listen on | `127.0.0.1` |
| `LISTEN_PORT` | Port to listen on | `50443` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Path to log file | `oai_gateway.log` |
| `REQUEST_LOG_FILE` | Path to request tracing file | `request_trace.log` |
| `OAI_DEFAULT_PROVIDER` | Default provider to use | `dummy` |

## TLS Certificate Setup

For local development, you can generate a self-signed certificate using the provided script:

```bash
./certs.sh
```

This script allows customization via environment variables:

| Environment Variable | Description | Default Value |
|----------------------|-------------|---------------|
| `CERT_PATH` | Output path for certificate | `cert.pem` |
| `KEY_PATH` | Output path for private key | `key.pem` |
| `DAYS` | Certificate validity in days | `365` |
| `CN` | Common Name for certificate | `localhost` |
| `RSA_BITS` | RSA key size in bits | `4096` |

## Running the Gateway

Run the gateway as a module:

```bash
python -m OAIGateway
```

Note: If running on port 443, elevated privileges may be required.

## Logging

The gateway includes comprehensive logging features:

- Console and file logging configured via environment variables
- Request and response details are logged with unique request IDs for traceability
- Request body information is sanitized to avoid logging sensitive data
- Client IP addresses and request headers are captured for security analysis
- Different log levels are used based on response status codes

### Standard Application Logs

Standard application logs are written to both console and the file specified by `LOG_FILE` (default: `oai_gateway.log`). These logs contain high-level information about application status, errors, and basic request information.

### Request Tracing

A dedicated request tracing system logs detailed information about all HTTP requests and responses to a separate file specified by `REQUEST_LOG_FILE` (default: `request_trace.log`). This tracing includes:

- Complete request and response cycles with unique request IDs
- Full HTTP headers (with sensitive authentication values redacted)
- Sanitized request bodies (message content replaced with length indicators)
- Sanitized response bodies (assistant responses replaced with length indicators)
- Request timing information
- Clear BEGIN/END markers for each request
- Visual separators between requests for easy log reading

You can customize both logging systems with these environment variables:
- `LOG_LEVEL`: Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL (default: INFO)
- `LOG_FILE`: Path to the standard application log file (default: oai_gateway.log)
- `REQUEST_LOG_FILE`: Path to the detailed request tracing file (default: request_trace.log)

## Provider System

The gateway uses a provider-based architecture to transform between OpenAI and backend formats:

1. Each provider implements the `Provider` interface
2. Providers are selected based on the requested model
3. Providers handle the transformation logic for specific backends
4. Available providers:
   - Azure OpenAI provider
   - Dummy provider (for testing)

To add additional providers, create a new module in the `Providers/backend` directory that implements the `Provider` interface.

## Endpoints

- `/v1/chat/completions`: Handles chat completion requests in OpenAI format
- `/health`: Health check endpoint with provider status
- `/*`: Catch-all handler that returns proper 404 errors in OpenAI format

## Request/Response Flow

1. Client sends an OpenAI-formatted request to the gateway
2. Gateway validates and identifies the appropriate provider
3. Provider transforms the request to its specific backend format
4. Gateway forwards the transformed request to the backend
5. Backend processes the request and returns a response
6. Provider transforms the backend response to OpenAI format
7. Gateway returns the OpenAI-formatted response to the client

## Request Transformation

The request transformation depends on the provider implementation. For example, the default Azure provider transforms OpenAI's "messages" format:

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

Into the Azure backend's "conversation" format:

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
- Limited model selection capability
- No authentication handling
- Self-signed certificates for development only

## Troubleshooting

- **Gateway fails to start**: Ensure the certificate and key files exist and are valid
- **Connection refused**: Verify the backend service is running at the configured URL
- **SSL errors**: Check that your client trusts the self-signed certificate
- **Request errors**: Examine the logs for details on request validation or transformation issues
- **Log file access issues**: Ensure the directory for the log file exists and is writable
- **Log file permissions**: If using a non-default log path, ensure write permissions

## Security Considerations

This gateway is intended for local development only. For production use, consider:

- Using proper certificates from a trusted CA
- Implementing authentication and authorization
- Adding rate limiting
- Containerizing the application
- Implementing more robust error handling and logging