"""Endpoint Registry — register, configure, and test reusable endpoints."""
import json
import random
import re
import shlex
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])
_VAR_PATTERN = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _resolve_template(text: str, context: dict) -> str:
    if not text:
        return text

    def lookup(match: re.Match) -> str:
        path = match.group(1).split(".")
        value = context
        for part in path:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return match.group(0)
        return str(value)

    return _VAR_PATTERN.sub(lookup, text)


def _replace_env_keys(text: str, values: dict[str, str]) -> str:
    result = text
    for key, value in values.items():
        result = result.replace(key, value)
    return result


def _find_unresolved_env_tokens(text: str) -> list[str]:
    """
    Detect unresolved env placeholders like OUC_API_HOST after replacement.
    This guards against calling invalid URLs for a selected environment.
    """
    if not text:
        return []
    return sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", text)))


def _mask_request_headers_for_display(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (headers or {}).items():
        lk = k.lower()
        if lk == "authorization" and "bearer" in v.lower():
            out[k] = "Bearer ***MASKED***"
        elif "api-key" in lk or lk == "x-api-key":
            out[k] = "***MASKED***"
        else:
            out[k] = v
    return out


def _build_curl_command(
    method: str,
    full_url: str,
    query_params: dict[str, str],
    headers: dict[str, str],
    body: str,
    verify_ssl: bool,
) -> str:
    """
    Reproducible curl for the resolved request. Secrets in headers are masked.
    """
    q = query_params or {}
    if q:
        url = f"{full_url}?{urlencode(list(q.items()), doseq=True)}"
    else:
        url = full_url
    masked = _mask_request_headers_for_display(dict(headers or {}))
    m = (method or "GET").upper()
    if m == "SOAP":
        m = "POST"
    parts: list[str] = ["curl -sS -L"]
    if not verify_ssl:
        parts.append("-k")
    parts += ["-X", m, shlex.quote(url)]
    for k, v in sorted(masked.items(), key=lambda kv: kv[0].lower()):
        parts += ["-H", shlex.quote(f"{k}: {v}")]
    if m in ("POST", "PUT", "PATCH", "DELETE") and body and body.strip():
        parts += ["--data-raw", shlex.quote(body)]
    oneline = " ".join(parts)

    lines: list[str] = ["curl -sS -L"]
    if not verify_ssl:
        lines[0] += " -k"
    lines[0] += " \\"
    lines.append(f"  -X {m} {shlex.quote(url)} \\")
    for k, v in sorted(masked.items(), key=lambda kv: kv[0].lower()):
        lines.append(f"  -H {shlex.quote(f'{k}: {v}')} \\")
    if m in ("POST", "PUT", "PATCH", "DELETE") and body and body.strip():
        lines.append(f"  --data-raw {shlex.quote(body)}")
    else:
        if lines and lines[-1].endswith(" \\"):
            lines[-1] = lines[-1].rstrip(" \\")
    multiline = "\n".join(lines)
    return f"{oneline}\n\n# Multiline (same request):\n{multiline}"


def _build_request_parts(
    ep: models.Endpoint,
    payload: schemas.EndpointTestRequest,
    env_map: dict[str, str],
) -> tuple[str, str, str, dict[str, str], str, dict[str, str]]:
    """Return method, full_url, request_path, headers, body_str, query_params (for display)."""
    context = {"input": payload.input_data, "variables": payload.input_data}
    base_src = payload.override_base_url if payload.override_base_url is not None else ep.base_url
    path_src = payload.override_path if payload.override_path is not None else ep.path
    method = (payload.override_method or ep.method or "GET").upper()
    if method == "SOAP":
        method = "POST"  # real HTTP: treat SOAP as POST body

    base_url = _replace_env_keys(base_src, env_map)
    path = _resolve_template(path_src, context)

    if payload.override_query_params is not None:
        raw_qp = dict(payload.override_query_params)
    else:
        raw_qp = dict(ep.query_params_template or {})
    query_params: dict[str, str] = {
        k: _resolve_template(str(v), context) for k, v in raw_qp.items()
    }

    body = _resolve_template(ep.body_template or "", context)
    full_url = f"{base_url}{path}"

    headers: dict[str, str] = dict(ep.headers or {})
    if ep.auth_type == "bearer":
        token = env_map.get("OUC_API_BEARER_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    if ep.auth_type == "api_key" and ep.auth_config:
        ref = (ep.auth_config or {}).get("secret_ref", "")
        if ref.startswith("env:"):
            key_name = ref.split("env:", 1)[1]
            if key_name in env_map:
                # generic header for tests — many APIs use X-API-Key; caller can set real headers on endpoint
                headers.setdefault("X-API-Key", env_map[key_name])

    return method, full_url, path, headers, body, query_params


@router.get("", response_model=list[schemas.EndpointOut])
def list_endpoints(
    environment: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Endpoint)
    if environment:
        q = q.filter(models.Endpoint.environment == environment)
    if is_active is not None:
        q = q.filter(models.Endpoint.is_active == is_active)
    return q.order_by(models.Endpoint.updated_at.desc()).all()


@router.post("", response_model=schemas.EndpointOut, status_code=status.HTTP_201_CREATED)
def create_endpoint(payload: schemas.EndpointCreate, db: Session = Depends(get_db)):
    ep = models.Endpoint(**payload.model_dump())
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


@router.get("/{endpoint_id}", response_model=schemas.EndpointOut)
def get_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    ep = db.get(models.Endpoint, endpoint_id)
    if not ep:
        raise HTTPException(404, "Endpoint not found")
    return ep


@router.patch("/{endpoint_id}", response_model=schemas.EndpointOut)
def update_endpoint(
    endpoint_id: int,
    payload: schemas.EndpointUpdate,
    db: Session = Depends(get_db),
):
    ep = db.get(models.Endpoint, endpoint_id)
    if not ep:
        raise HTTPException(404, "Endpoint not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ep, k, v)
    db.commit()
    db.refresh(ep)
    return ep


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    ep = db.get(models.Endpoint, endpoint_id)
    if not ep:
        raise HTTPException(404, "Endpoint not found")
    db.delete(ep)
    db.commit()


@router.post("/{endpoint_id}/test")
def test_endpoint(
    endpoint_id: int,
    payload: schemas.EndpointTestRequest,
    db: Session = Depends(get_db),
):
    """
    Test an endpoint. With `real_http: false` (default) returns a simulated response.
    With `real_http: true` issues a real request via httpx using resolved URL/params/body
    and environment settings (e.g. OUC host, bearer token).
    """
    ep = db.get(models.Endpoint, endpoint_id)
    if not ep:
        raise HTTPException(404, "Endpoint not found")

    settings = (
        db.query(models.EnvironmentSetting)
        .filter(
            models.EnvironmentSetting.environment == payload.environment,
            models.EnvironmentSetting.is_active == True,  # noqa: E712
        )
        .all()
    )
    env_map = {s.key: s.value for s in settings}
    verify_ssl = (env_map.get("OUC_API_VERIFY_SSL", "true") or "true").lower() not in (
        "false",
        "0",
        "no",
    )
    try:
        timeout_s = float(env_map.get("HTTP_TEST_TIMEOUT", str(ep.timeout_seconds or 30)))
    except ValueError:
        timeout_s = float(ep.timeout_seconds or 30)

    method, full_url, path, headers, body, query_params = _build_request_parts(ep, payload, env_map)
    unresolved_tokens = _find_unresolved_env_tokens(full_url)
    if unresolved_tokens:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unresolved environment placeholders in URL for "
                f"environment '{payload.environment}': {unresolved_tokens}. "
                "Define matching keys in Environment Settings or override base URL."
            ),
        )

    auth_preview: dict[str, Any] = {"auth_type": ep.auth_type}
    if ep.auth_type == "bearer":
        token = env_map.get("OUC_API_BEARER_TOKEN")
        auth_preview["authorization"] = f"Bearer {'***MASKED***' if token else '<missing token>'}"
    if "Authorization" in headers:
        auth_preview["authorization"] = "Bearer ***MASKED***" if "Bearer" in headers["Authorization"] else "***MASKED***"

    masked_request_headers = _mask_request_headers_for_display(dict(headers))
    curl_command = _build_curl_command(method, full_url, query_params, headers, body, verify_ssl)

    if not payload.real_http:
        success = random.random() > 0.05
        response_body = (
            {
                "data": {"id": "tst_001", "value": 42.0},
                "meta": {"version": "v1", "echoed_headers": list((ep.headers or {}).keys())},
            }
            if success
            else None
        )
        out_text = (
            json.dumps(response_body, indent=2, ensure_ascii=False)
            if success and response_body is not None
            else (None if success else "Simulated upstream service unavailable")
        )
        return {
            "mode": "simulated",
            "endpoint_id": endpoint_id,
            "name": ep.name,
            "environment": payload.environment,
            "registry_environment": ep.environment,
            "url": full_url,
            "method": method,
            "auth_type": ep.auth_type,
            "auth_preview": auth_preview,
            "verify_ssl": verify_ssl,
            "request_headers": masked_request_headers,
            "curl_command": curl_command,
            "resolved_query_params": query_params,
            "resolved_body": body or None,
            "input_data": payload.input_data,
            "tested_at": datetime.utcnow().isoformat(),
            "status": "ok" if success else "error",
            "status_code": 200 if success else 503,
            "latency_ms": random.randint(80, 600),
            "response_body": response_body,
            "output": out_text,
            "error": None if success else "Simulated upstream service unavailable",
        }

    # --- Real HTTP ---
    t0 = time.perf_counter()
    request_error: str | None = None
    status_code: int = 0
    response_text: str | None = None
    response_json: Any = None
    response_headers: dict[str, str] | None = None
    try:
        req_kwargs: dict[str, Any] = {
            "method": method,
            "url": full_url,
            "headers": headers,
            "params": query_params or None,
            "timeout": httpx.Timeout(timeout_s),
            "verify": verify_ssl,
            "follow_redirects": True,
        }
        if method in ("POST", "PUT", "PATCH", "DELETE") and body and body.strip():
            try:
                req_kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                req_kwargs["content"] = body.encode("utf-8")
        with httpx.Client() as client:
            resp = client.request(**req_kwargs)
        status_code = resp.status_code
        response_text = resp.text
        response_headers = {k: v for k, v in resp.headers.items()}
        try:
            response_json = resp.json()
        except Exception:
            response_json = None
    except httpx.RequestError as exc:
        request_error = str(exc)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    ok = request_error is None and 200 <= status_code < 300
    body_value = response_json if response_json is not None else (response_text[:20000] if response_text else None)
    if request_error is not None:
        output = request_error
    elif response_json is not None:
        output = json.dumps(response_json, indent=2, ensure_ascii=False)
    else:
        output = response_text[:20000] if response_text else ""

    return {
        "mode": "http",
        "endpoint_id": endpoint_id,
        "name": ep.name,
        "environment": payload.environment,
        "registry_environment": ep.environment,
        "url": full_url,
        "method": method,
        "auth_type": ep.auth_type,
        "auth_preview": auth_preview,
        "verify_ssl": verify_ssl,
        "request_headers": masked_request_headers,
        "curl_command": curl_command,
        "resolved_query_params": query_params,
        "resolved_body": body or None,
        "input_data": payload.input_data,
        "tested_at": datetime.utcnow().isoformat(),
        "status": "ok" if ok else "error",
        "status_code": status_code,
        "latency_ms": latency_ms,
        "response_body": body_value,
        "response_headers": response_headers,
        "output": output,
        "error": request_error,
    }
