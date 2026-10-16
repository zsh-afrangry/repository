"""A dedicated local service credential, never a model argument or portal cookie."""
import hmac
import os
from pathlib import Path
from fastapi import Header, HTTPException


def require_assistant(authorization: str = Header(default="")) -> None:
    path = Path(os.environ.get("KM_ASSISTANT_TOKEN_FILE", str(Path.home() / ".config/knowledgemap/assistant-token")))
    try:
        if not path.is_absolute() or path.stat().st_mode & 0o077:
            raise ValueError("credential permissions")
        token = path.read_text().strip()
        if len(token) < 32 or len(token) > 256 or not token.isascii():
            raise ValueError("credential shape")
    except (OSError, ValueError):
        raise HTTPException(503, detail={"code": "assistant_not_configured", "message": "助手接口凭据未配置"}) from None
    if not hmac.compare_digest(authorization, "Bearer " + token):
        raise HTTPException(401, detail={"code": "unauthorized", "message": "需要专用助手凭据"})
