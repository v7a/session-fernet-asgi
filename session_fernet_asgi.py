"""Provides an encrypted and signed session that is stored as a Fernet token on the client."""

from dataclasses import dataclass
import json
from typing import Protocol, Optional, Any

from cryptography.fernet import Fernet, InvalidToken
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

__version__ = "0.1"


class EncodeDataFunction(Protocol):
    """Encode a Python dict to bytes."""

    def __call__(self, data: dict) -> bytes:
        pass


class DecodeDataFunction(Protocol):
    """Decode bytes to a Python dict."""

    def __call__(self, data: bytes) -> dict:
        pass


Seconds = int


@dataclass(frozen=True)
class CookieConfiguration:
    """Configure the session cookie."""

    name: str = "session"
    max_age: Seconds = 24 * 60 * 60
    same_site: str = "lax"
    domain: Optional[str] = None
    path: str = "/"
    httponly: bool = True
    secure: bool = False


def _json_dumps_bytes(data: dict) -> bytes:
    return json.dumps(data).encode("utf-8")


def _json_loads_bytes(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


class SessionMiddleware(BaseHTTPMiddleware):
    """The session middleware implementation.

    :param secret_key: Secret key used to encrypt and decrypt the session
    :param cookie_config: Configure how the session cookie is stored
    :param default_value: Default session to use if none or invalid session
    :param encode_data: Callable to transform a Python dictionary to bytes
    :param decode_data: Callable to transform bytes to a Python dictionary
    :param fernet_backend: Backend passed to cryptography.Fernet (default: OpenSSL)
    """

    def __init__(
        self,
        app: Any,
        secret_key: bytes,
        cookie_config: CookieConfiguration,
        default_value: dict = None,
        encode_data: EncodeDataFunction = _json_dumps_bytes,
        decode_data: DecodeDataFunction = _json_loads_bytes,
        fernet_backend: Any = None,
    ):
        super().__init__(app)
        self.cookie_config = cookie_config
        self.default_value = default_value or {}
        self.encode_data = encode_data
        self.decode_data = decode_data
        self.fernet = Fernet(secret_key, fernet_backend)

    def _load(self, request: Request) -> dict:
        try:
            return self.decode_data(
                self.fernet.decrypt(
                    request.cookies[self.cookie_config.name].encode("utf-8"),
                    self.cookie_config.max_age,
                )
            )
        except (KeyError, InvalidToken, json.JSONDecodeError, UnicodeDecodeError):
            return self.default_value.copy()

    def _dump(self, data: dict) -> str:
        return self.fernet.encrypt(self.encode_data(data)).decode("utf-8")

    async def dispatch(self, request: Request, call_next):
        request.scope["session"] = self._load(request)
        response = await call_next(request)
        response.set_cookie(
            self.cookie_config.name,
            self._dump(request.scope["session"]),
            max_age=self.cookie_config.max_age,
            path=self.cookie_config.path,
            domain=self.cookie_config.domain,
            secure=self.cookie_config.secure,
            httponly=self.cookie_config.httponly,
            samesite=self.cookie_config.same_site,
        )
        return response
