from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import ssl
import struct
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.models.domain import RemoteStationConnection

PROTOCOL = "PQRP/1"
logger = logging.getLogger(__name__)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def payload_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _secret_path(reference: str | None, label: str) -> str:
    if not reference:
        raise HTTPException(status_code=422, detail=f"远程连接未配置{label}引用")
    value = os.environ.get(reference)
    if not value:
        raise HTTPException(
            status_code=503,
            detail=f"运行环境没有注入{label}（配置引用：{reference}）",
        )
    return value


def _read_exact(stream: ssl.SSLSocket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.recv(remaining)
        if not chunk:
            raise ConnectionError("远程代理提前断开连接")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_agent_request(
    connection: RemoteStationConnection,
    message_type: str,
    body: dict,
) -> dict:
    if connection.transport != "TLS_TCP":
        raise HTTPException(status_code=422, detail="仅允许使用双向 TLS 的 TCP/IP 连接")
    try:
        ca_file = _secret_path(connection.trusted_ca_ref, "受信任根证书")
        cert_file = _secret_path(connection.client_certificate_ref, "客户端证书")
        key_file = _secret_path(connection.client_private_key_ref, "客户端私钥")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    except HTTPException:
        raise
    except (OSError, ssl.SSLError) as exc:
        logger.exception("Failed to load remote station TLS material")
        raise HTTPException(
            status_code=503,
            detail="无法加载目标上位机连接所需的证书或密钥",
        ) from exc
    envelope = {
        "protocol": PROTOCOL,
        "messageId": str(uuid4()),
        "sentAt": datetime.now(UTC).isoformat(),
        "nonce": uuid4().hex,
        "agentId": connection.agent_id,
        "type": message_type,
        "body": body,
        "bodyHash": payload_hash(body),
    }
    encoded = canonical_json(envelope)
    if len(encoded) > connection.max_package_bytes:
        raise HTTPException(status_code=422, detail="远程参数包超过该连接允许的大小")
    try:
        with socket.create_connection(
            (connection.host, connection.port),
            timeout=connection.connect_timeout_seconds,
        ) as raw_socket:
            with context.wrap_socket(
                raw_socket,
                server_hostname=connection.server_name or connection.host,
            ) as stream:
                stream.settimeout(connection.connect_timeout_seconds)
                stream.sendall(struct.pack(">I", len(encoded)) + encoded)
                response_size = struct.unpack(">I", _read_exact(stream, 4))[0]
                if response_size <= 0 or response_size > connection.max_package_bytes:
                    raise ConnectionError("远程代理返回的数据包大小不合法")
                response = json.loads(_read_exact(stream, response_size).decode("utf-8"))
    except (OSError, ssl.SSLError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Remote station agent request failed")
        raise HTTPException(status_code=502, detail="无法连接目标上位机通讯程序") from exc
    if response.get("protocol") != PROTOCOL or response.get("agentId") != connection.agent_id:
        raise HTTPException(status_code=502, detail="目标上位机代理身份或协议版本不匹配")
    response_body = response.get("body")
    if not isinstance(response_body, dict) or response.get("bodyHash") != payload_hash(
        response_body
    ):
        raise HTTPException(status_code=502, detail="目标上位机代理响应完整性校验失败")
    if response.get("type") == "ERROR":
        logger.warning(
            "Remote station agent rejected request: %s",
            response_body.get("message"),
        )
        raise HTTPException(
            status_code=502,
            detail="目标上位机通讯程序拒绝了本次请求",
        )
    return response_body
