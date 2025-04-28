# OpenAI API Gateway

A modular API gateway that transforms OpenAI API requests into provider-specific formats and provides local TLS termination.

## Current Implementation Status

- **ASGI Server**: FastAPI application with Uvicorn server implementation
- **TLS Termination**: HTTPS support with configurable certificates via `certs.sh`
- **Request/Response Middleware**: Comprehensive logging and metrics collection
- **API Endpoints**: Initial implementation of `/chat/completions` endpoint
- **Command-line Interface**: Configurable via environment variables and CLI arguments

## Planned Features

- Transforms request payloads between OpenAI and backend formats
- Extensible provider system for different backend services
- Proxies requests to configured backend services
- Transforms backend responses back to OpenAI format

## Technical Stack

- **FastAPI**: Web server framework
- **Pydantic**: Request/response validation
- **HTTPX**: HTTP client for backend communication
- **Uvicorn**: ASGI server implementation

## Configuration

The service can be configured through:
- Environment variables
- Command-line arguments
- Local SSL certificates (generated or provided)

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Generate SSL certificates: `./certs.sh`
3. Run the service: `python -m OAIGateway [options]`

