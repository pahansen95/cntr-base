from fastapi.responses import JSONResponse
from . import app

### Routes

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def unmatched(path: str):
    """Catch-all route for unmatched requests."""
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": f"Route '/{path}' not found"}
    )
