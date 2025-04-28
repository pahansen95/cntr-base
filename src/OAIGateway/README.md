# OpenAI API Gateway

A modular API gateway that transforms OpenAI API requests into provider-specific formats and provides local TLS termination.

## Features

- Accepts HTTPS requests following OpenAI API structure
- Transforms request payloads between OpenAI and backend formats
- Extensible provider system for different backend services
- Proxies requests to configured backend services
- Transforms backend responses back to OpenAI format
- Terminates TLS locally with provided certificates
- Comprehensive error handling and logging
- Configuration via environment variables or command-line arguments

