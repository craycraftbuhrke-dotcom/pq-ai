from fastapi import HTTPException, Request


async def read_limited_request_body(request: Request, max_bytes: int, label: str = "导入文件") -> bytes:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Content-Length 不是有效整数") from exc
        if declared_size < 0:
            raise HTTPException(status_code=400, detail="Content-Length 不能为负数")
        if declared_size > max_bytes:
            raise HTTPException(status_code=413, detail=f"{label}超过系统允许的大小")

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > max_bytes:
            raise HTTPException(status_code=413, detail=f"{label}超过系统允许的大小")
        content.extend(chunk)
    return bytes(content)
