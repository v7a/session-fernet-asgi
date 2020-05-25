"""Provides an encrypted and signed session that is stored as a Fernet token on the client."""

from dataclasses import dataclass
import json
from typing import Protocol, Optional, Any

import http.cookies
from cryptography.fernet import Fernet, InvalidToken
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# NOTE: remove once starlette supports samesite argument to Response.set_cookie
http.cookies.Morsel._reserved["samesite"] = "SameSite"  # type: ignore  # pylint: disable=all

__version__ = "0.2"


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


#
# NOTE: to be replaced once starlette supports samesite argument to Response.set_cookie
#
def _set_cookie(  # pylint: disable=too-many-arguments
    response,
    key: str,
    value: str = "",
    max_age: int = None,
    expires: int = None,
    path: str = "/",
    domain: str = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: str = "lax",
) -> None:
    cookie = http.cookies.SimpleCookie()  # type: ignore
    cookie[key] = value
    if max_age is not None:
        cookie[key]["max-age"] = max_age
    if expires is not None:
        cookie[key]["expires"] = expires
    if path is not None:
        cookie[key]["path"] = path
    if domain is not None:
        cookie[key]["domain"] = domain
    if secure:
        cookie[key]["secure"] = True
    if httponly:
        cookie[key]["httponly"] = True
    if samesite is not None:
        assert samesite.lower() in [
            "strict",
            "lax",
            "none",
        ], "samesite must be either 'strict', 'lax' or 'none'"
        cookie[key]["samesite"] = samesite
    cookie_val = cookie.output(header="").strip()
    response.raw_headers.append((b"set-cookie", cookie_val.encode("latin-1")))


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
        self.fernet = Fernet(secret_key, fernet_backend)  # type: ignore

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
        # NOTE: replace with Response.set_cookie once samesite argument is supported
        _set_cookie(
            response,
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
