import time
from fastapi import Request, HTTPException, status  # type: ignore

# requests per window
RATE_LIMIT = 60        # 60 requests
WINDOW_SECONDS = 60    # per 60 seconds

# in-memory store
client_requests = {}

async def rate_limiter(request: Request):
    client_ip = request.client.host
    now = time.time()

    window_start = now - WINDOW_SECONDS

    # init
    if client_ip not in client_requests:
        client_requests[client_ip] = []

    # remove old requests
    client_requests[client_ip] = [
        ts for ts in client_requests[client_ip]
        if ts > window_start
    ]

    # check limit
    if len(client_requests[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later."
        )

    # record request
    client_requests[client_ip].append(now)
