"""Test the session middleware."""

from session_fernet_asgi import SessionMiddleware, CookieConfiguration

from cryptography.fernet import Fernet

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient


session_value = None


def _make_client(max_age: int) -> TestClient:
    def populate_session(request: Request) -> Response:
        request.session["value"] += 120
        return Response()

    def read_session(request: Request) -> Response:
        global session_value
        session_value = request.session["value"]
        return Response()

    return TestClient(
        Starlette(
            routes=[
                Route("/populate_session", populate_session),
                Route("/read_session", read_session),
            ],
            middleware=[
                Middleware(
                    SessionMiddleware,
                    secret_key=Fernet.generate_key(),
                    cookie_config=CookieConfiguration(max_age=max_age),
                    default_value={"value": 0},
                )
            ],
        ),
        raise_server_exceptions=True,
    )


def test_middleware():
    client = _make_client(24 * 60 * 60)

    # default value of 0
    client.get("/read_session")
    assert session_value == 0

    client.get("/populate_session")
    client.get("/read_session")
    assert session_value == 120

    client.get("/read_session", cookies={CookieConfiguration().name: "invalid data"})
    assert session_value == 0


def test_middleware_expired():
    client = _make_client(0)

    client.get("/populate_session")
    client.get("/read_session")
    assert session_value == 0
