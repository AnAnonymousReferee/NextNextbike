"""WSGI server for the BonnBike backend and frontend static assets."""

import json
import mimetypes
import os
import sys
import traceback
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs

from backend.backend_api import (
    change_password,
    getAllBikes,
    getNextNextbike,
    markFav,
    register_user,
    reset_password,
    userLogin,
)
from backend.mail import ConsoleMailSender, PasswordResetMailSender

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = BASE_DIR / "frontend"


def _parse_query_string(query_string):
    if not query_string:
        return {}
    return {k: v[0] for k, v in parse_qs(query_string, keep_blank_values=True).items()}


def _parse_body(environ):
    content_length = environ.get("CONTENT_LENGTH") or "0"
    try:
        length = int(content_length)
    except ValueError:
        length = 0

    body_bytes = environ["wsgi.input"].read(length) if length > 0 else b""
    if not body_bytes:
        return {}

    content_type = environ.get("CONTENT_TYPE", "")
    if content_type.startswith("application/json"):
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except ValueError:
            return {}

    return _parse_query_string(body_bytes.decode("utf-8"))


def _parse_api_headers(environ):
    api_key = (
        environ.get("HTTP_X_API_KEY")
        or environ.get("HTTP_API_KEY")
        or environ.get("HTTP_API_KEY_USER")
    )
    if not api_key:
        return {}
    return {"api-key": api_key}


def _configured_mail_sender():
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return ConsoleMailSender()

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    use_tls = os.environ.get("SMTP_USE_TLS", "true").strip().lower() != "false"
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    from_address = os.environ.get("MAIL_FROM", "noreply@example.org")
    reset_url_template = os.environ.get(
        "PASSWORD_RESET_URL_TEMPLATE",
        "http://localhost:8000/api/password-reset/confirm?token={token}",
    )
    return PasswordResetMailSender(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        from_address=from_address,
        username=smtp_username,
        password=smtp_password,
        use_tls=use_tls,
        reset_url_template=reset_url_template,
    )


def _response(body, status=HTTPStatus.OK):
    if body is None:
        payload = b""
    else:
        payload = json.dumps(body).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(payload))),
    ]
    return status, payload, headers


def _static_file_response(path):
    if path in ("", "/"):
        path = "/index.html"

    safe_path = (FRONTEND_ROOT / path.lstrip("/")).resolve()
    print(f"DEBUG: static request path={path}, safe_path={safe_path}", file=sys.stderr)

    if not str(safe_path).startswith(str(FRONTEND_ROOT)):
        print(f"DEBUG: forbidden static path {safe_path}", file=sys.stderr)
        return HTTPStatus.FORBIDDEN, b"Forbidden", [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", "9"),
        ]

    if not safe_path.exists() or not safe_path.is_file():
        print(f"DEBUG: static file not found {safe_path}", file=sys.stderr)
        return HTTPStatus.NOT_FOUND, b"Not Found", [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", "9"),
        ]

    try:
        with open(safe_path, "rb") as handle:
            payload = handle.read()
    except Exception as exc:
        print(f"DEBUG: error reading static file {safe_path}: {exc}", file=sys.stderr)
        raise

    content_type = mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(payload))),
    ]
    return HTTPStatus.OK, payload, headers


def _application_response(start_response, status, payload, headers):
    if isinstance(status, int):
        status = HTTPStatus(status)

    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    elif isinstance(payload, bytearray):
        payload = bytes(payload)
    elif not isinstance(payload, (bytes, memoryview)):
        payload = str(payload).encode("utf-8")

    start_response(f"{status.value} {status.phrase}", headers)
    return [payload]


def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    method = environ.get("REQUEST_METHOD", "GET")
    queries = _parse_query_string(environ.get("QUERY_STRING", ""))
    body = _parse_body(environ)
    headers = _parse_api_headers(environ)
    mail_sender = _configured_mail_sender()

    try:
        if path == "/api/nextbike" and method == "GET":
            status, response_body = getNextNextbike(queries)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/bikes" and method == "GET":
            status, response_body = getAllBikes(headers, queries)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/login" and method == "POST":
            status, response_body = userLogin(body)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/register" and method == "POST":
            status, response_body = register_user(body)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/password-reset" and method == "POST":
            status, response_body = change_password(body, mail_sender=mail_sender)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/password-reset/confirm" and method == "POST":
            status, response_body = reset_password(body)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        if path == "/api/favourite" and method == "POST":
            status, response_body = markFav(headers, body)
            return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])

        status, payload, headers = _static_file_response(path)
        return _application_response(start_response, status, payload, headers)
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        status, response_body = HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}
        return _application_response(start_response, status, _response(response_body, status)[1], _response(response_body, status)[2])


def run_server(host="127.0.0.1", port=8000):
    from wsgiref.simple_server import make_server

    print(f"BonnBike backend running on http://{host}:{port}")
    with make_server(host, port, application) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
