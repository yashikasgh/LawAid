import time
from fastapi import Request

async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    user_id = "anonymous"
    auth_header = request.headers.get("authorization")
    if auth_header:
        user_id = "authenticated"

    print(
        f"[AUDIT] {request.method} {request.url.path} "
        f"| status={response.status_code} | user={user_id} "
        f"| ip={request.client.host} | duration={duration:.3f}s"
    )
    return response