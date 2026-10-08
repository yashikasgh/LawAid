"""Short-lived OTP state used to authorize final FIR approval.

The OTP is deliberately kept separate from the FIR hash: it authorizes the
officer action, while the SHA-256 value protects the resulting PDF bytes.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Dict, Tuple


OTP_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
_pending_otps: Dict[Tuple[int, str], dict] = {}


def issue_approval_otp(officer_id: int, draft_id: str) -> str:
    """Create a short-lived OTP for one officer and FIR draft."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    _pending_otps[(officer_id, draft_id)] = {
        "code_hash": hashlib.sha256(code.encode("utf-8")).hexdigest(),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES),
        "attempts": 0,
    }
    return code


def verify_approval_otp(officer_id: int, draft_id: str, code: str) -> bool:
    """Consume a valid OTP. A code can never approve more than one FIR."""
    key = (officer_id, draft_id)
    pending = _pending_otps.get(key)
    if not pending:
        return False

    if pending["expires_at"] <= datetime.now(timezone.utc):
        _pending_otps.pop(key, None)
        return False

    pending["attempts"] += 1
    supplied_hash = hashlib.sha256((code or "").encode("utf-8")).hexdigest()
    valid = secrets.compare_digest(pending["code_hash"], supplied_hash)

    if valid or pending["attempts"] >= MAX_OTP_ATTEMPTS:
        _pending_otps.pop(key, None)

    return valid
