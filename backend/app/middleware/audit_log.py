import time
from fastapi import Request
from app.core.database import SessionLocal
from app.models.audit_log import AuditLog

async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    duration_ms = int(duration * 1000)

    user_id = "anonymous"
    auth_header = request.headers.get("authorization")
    if auth_header:
        user_id = "authenticated"

    ip = request.client.host if request.client else "127.0.0.1"

    # Console log
    print(
        f"[AUDIT] {request.method} {request.url.path} "
        f"| status={response.status_code} | user={user_id} "
        f"| ip={ip} | duration={duration:.3f}s"
    )

    # Database persistence (P1 Task 11)
    try:
        db = SessionLocal()
        entry = AuditLog(
            user_id=user_id,
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            ip_address=ip,
            duration_ms=duration_ms,
        )
        db.add(entry)
        db.commit()
        db.close()
    except Exception:
        # Never break the request flow if audit storage fails
        pass

    return response