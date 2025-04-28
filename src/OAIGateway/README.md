# OpenAI API Gateway

A modular API gateway that transforms OpenAI API requests into provider-specific formats and provides local TLS termination.

## Current Implementation Status

- **ASGI Server**: FastAPI application with Uvicorn server implementation
- **TLS Termination**: HTTPS support with configurable certificates via `certs.sh`
- **Request/Response Middleware**: Comprehensive logging and metrics collection
- **API Endpoints**: 
  - `/chat/completions` - Transforms OpenAI chat completion requests to Azure OpenAI format
  - `/models` - Lists available models with a hardcoded set of supported models
  - Fallback route handling for unmatched paths
- **Command-line Interface**: Configurable via environment variables and CLI arguments
- **Azure OpenAI Integration**: Transforms requests to Azure OpenAI API format and handles responses

## Models Support

The following models are currently supported for Azure OpenAI deployments:
- gpt-4o
- gpt-4.1, gpt-4.1-mini, gpt-4.1-nano
- o3, o4-mini

## Configuration

The service can be configured through:

- **Environment Variables**:
  - `AZURE_OPENAI_API_BASE`: Base URL for Azure OpenAI API
  - `AZURE_OPENAI_API_KEY`: API key for Azure OpenAI
  - `AZURE_OPENAI_API_VERSION`: API version for Azure OpenAI
  - `LISTEN_HOST`: Host to listen on (default: 127.0.0.1)
  - `LISTEN_PORT`: Port to listen on (default: 8000)
  - `CERT_PATH`: Path to SSL certificate (default: ./cert.pem)
  - `KEY_PATH`: Path to SSL key (default: ./cert.key)
  - `LOG_LEVEL`: Logging level (default: INFO)
  - `HTTP_METRICS`: Path to HTTP metrics log file (default: ./http.metrics)

- **Command-line Arguments**:
  - `--listen-host`: Host to listen on
  - `--listen-port`: Port to listen on
  - `--cert-path`: Path to SSL certificate
  - `--cert-key`: Path to SSL key

- **Local SSL Certificates**: Generated or provided via `certs.sh`

## Technical Stack

- **FastAPI**: Web server framework
- **Pydantic**: Request/response validation and data modeling
- **HTTPX**: HTTP client for backend communication
- **Uvicorn**: ASGI server implementation with SSL support

## Usage

1. Install dependencies: `pip install -r requirements.txt`
2. Set required environment variables for Azure OpenAI:
   ```bash
   export AZURE_OPENAI_API_BASE="https://your-azure-resource.openai.azure.com"
   export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
   export AZURE_OPENAI_API_VERSION="2024-04-01-preview"
   ```
3. Set up TLS (see TLS Configuration section below)
4. Run the service: `python -m OAIGateway [options]`

## TLS Configuration

The gateway requires TLS for secure communication. Follow these steps to set up TLS:

### A) Generate Self-Signed Certificates

The included `certs.sh` script generates self-signed certificates for development:

```bash
# Export File Locations
export CERT_PATH="/path/to/cert.pem"
export KEY_PATH="/path/to/key.pem"
# Generate Certs
CN="mydomain.local" DAYS=365 RSA_BITS=4096 \
  ./certs.sh
```

Configuration options for `certs.sh`:
- `CERT_PATH`: Certificate output path (default: cert.pem)
- `KEY_PATH`: Private key output path (default: key.pem)
- `DAYS`: Certificate validity period in days (default: 365)
- `CN`: Common Name for the certificate (default: localhost)
- `RSA_BITS`: RSA key size (default: 4096)

The script generates certificates with Subject Alternative Names for:
- The specified Common Name
- localhost
- 127.0.0.1

### B) Configure Clients for Self-Signed Certificates

For OpenAI Codex CLI (a Node.js client):

```bash
# Export the path to your certificate
export NODE_EXTRA_CA_CERTS="${CERT_PATH}"
```

For Python clients:

```python
import requests

# Option 1: Provide certificate
requests.get("https://localhost:8000", verify="${CERT_PATH}")

# Option 2: Disable verification (NOT recommended for production)
requests.get("https://localhost:8000", verify=False)
```

For curl:

```bash
# Provide certificate
curl --cacert "${CERT_PATH}" https://localhost:8000

# Disable verification (NOT recommended for production)
curl -k https://localhost:8000
```

## Client Usage Example

The gateway can be used as a drop-in replacement for the OpenAI API:

```python
import openai

openai.base_url = "https://localhost:8000"
openai.api_key = "dummy-key"  # The gateway does not validate this

response = openai.chat.completions.create(
    model="gpt-4.1-nano",  # Will be mapped to the appropriate Azure deployment
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)
```