import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def request(method, url, headers=None, data=None):
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = Request(url, data=body, method=method)
    headers = headers or {}
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8")


if __name__ == "__main__":
    base = "http://127.0.0.1:8000"
    print("root", request("GET", base))
    print(
        "register",
        request(
            "POST",
            base + "/api/register",
            {"Content-Type": "application/json"},
            {
                "username": "testuser2026",
                "email": "testuser2026@example.org",
                "passwort": "Testpass2026!",
            },
        ),
    )
    print(
        "login",
        request(
            "POST",
            base + "/api/login",
            {"Content-Type": "application/json"},
            {"username": "testuser2026", "passwort": "Testpass2026!"},
        ),
    )
