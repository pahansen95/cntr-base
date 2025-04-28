import logging, time, os
from fastapi import FastAPI, Request, Response

### Logging
logger = logging.getLogger(__name__)
# do no setup; let the ASGI Server handle it

### Metrics
metrics = logging.getLogger(f'{__name__}/metrics')
metrics.propagate = False
metrics.setLevel('DEBUG') # Maximum Metrics
metrics_handler = logging.FileHandler(os.environ.get('HTTP_METRICS', './http.metrics'))
metrics_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
metrics.addHandler(metrics_handler)
metrics.info('Initialized')

# ------------------- FastAPI App -------------------

app = FastAPI(
    title="OpenAI API Gateway",
    description="A local gateway proxy that transforms OpenAI API requests to backend format",
    version="0.1.0"
)

### Middleware

@app.middleware("http")
async def trace(request: Request, call_next):
    request_id = time.monotonic_ns()
    start_time = time.time()
    
    # Extract request details
    client_host = request.client.host if request.client else "unknown"
    client_port = request.client.port if request.client else "unknown"
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    # Trace request
    metrics.info(f'{request_id}: Request received @ {start_time:.6f}')
    metrics.debug(f'{request_id}: {request.method} {request.url.path} from {client_host}:{client_port}')
    
    # Log headers (sanitizing auth data)
    safe_headers = headers.copy()
    for sensitive in ['authorization', 'api-key', 'x-api-key']:
        if sensitive in safe_headers:
            safe_headers[sensitive] = '[REDACTED]'
    
    metrics.debug(f'{request_id}: Headers: {safe_headers}')
    if query_params:
        metrics.debug(f'{request_id}: Query params: {query_params}')
    
    # Log request body for non-GET requests (potentially containing data)
    if request.method != "GET":
        try:
            body_bytes = await request.body()
            # Create a new request with the consumed body
            request = Request(
                scope=request.scope,
                receive=request._receive
            )
            # Store the body for later use by the route handlers
            request.state.body = body_bytes
            
            # Try to parse as JSON if content-type suggests it's JSON
            if 'application/json' in headers.get('content-type', ''):
                try:
                    import json
                    body_json = json.loads(body_bytes)
                    # Redact sensitive fields in JSON
                    if isinstance(body_json, dict):
                        for key in body_json.keys():
                            if any(sensitive in key.lower() for sensitive in ['key', 'token', 'password', 'secret']):
                                body_json[key] = '[REDACTED]'
                    metrics.debug(f'{request_id}: Request body (JSON): {body_json}')
                except:
                    # Not valid JSON or other issue
                    if len(body_bytes) < 1000:  # Don't log large binary payloads
                        metrics.debug(f'{request_id}: Request body: {body_bytes}')
            else:
                # Non-JSON body, log limited info
                metrics.debug(f'{request_id}: Request body size: {len(body_bytes)} bytes')
        except Exception as e:
            metrics.warning(f'{request_id}: Failed to capture request body: {str(e)}')
    
    # Process request
    try:
        response = await call_next(request)
        
        # Trace response
        end_time = time.time()
        duration = end_time - start_time
        metrics.info(f'{request_id}: Response sent @ {end_time:.6f} (took {duration:.6f}s)')
        metrics.debug(f'{request_id}: Status {response.status_code}')
        metrics.debug(f'{request_id}: Response headers: {dict(response.headers)}')
        
        # Log response size if available
        content_length = response.headers.get('content-length')
        if content_length:
            metrics.debug(f'{request_id}: Response size: {content_length} bytes')
        
        # For error responses, try to log the response body
        if response.status_code >= 400:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Create a new response with the consumed body
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            
            try:
                if 'application/json' in response.headers.get('content-type', ''):
                    import json
                    body_json = json.loads(body)
                    metrics.debug(f'{request_id}: Error response body: {body_json}')
            except:
                if len(body) < 1000:  # Don't log large responses
                    metrics.debug(f'{request_id}: Error response body: {body}')
    except Exception as e:
        # Log any unhandled exceptions during request processing
        end_time = time.time()
        duration = end_time - start_time
        metrics.error(f'{request_id}: Unhandled exception after {duration:.6f}s: {str(e)}')
        raise
        
    return response

### Local Imports
from .chat_completions import *
from .fallback import * # Make this last
