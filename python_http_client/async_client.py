"""Asynchronous Python HTTP Client Module"""

from collections import namedtuple
import http
from typing import Optional
from urllib.error import URLError, HTTPError

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError

from .client import Client, Response
from .exceptions import handle_error


class AiohttpClientSessionError(ValueError):
    """Invalid aiohttp.ClientSession error"""


class AsyncResponse(Response):
    def __init__(self, code, body, headers):
        self._status_code = code
        self._body = body
        self._headers = headers


class AsyncClient(Client):
    """Main async python HTTP client class"""
    def __init__(
        self, *args, client_session: Optional[ClientSession] = None, **kwargs
    ):
        """Create async Python HTTP client instance

        :param ClientSession client_session: aiohttp.ClientSession instance,
                                             optional, defaults to None
        """

        super().__init__(*args, **kwargs)
        self._aiohttp_client_session = client_session

    @property
    def client_session(self):
        """aiohttp.ClientSession instance"""
        return self._aiohttp_client_session

    @client_session.setter
    def client_session(self, session: ClientSession):
        """Apply aiohttp.ClientSession instance

        The only ClientSession instance can be applied. Otherwise
        AiohttpClientSessionError will be raised.

        :param ClientSession session: aiohttp.ClientSession instance
        :raises AiohttpClientSessionError: internal ClientSession exists
                                           or another external has already
                                           been applied
        """
        if self.client_session:
            raise AiohttpClientSessionError(
                'aiohttp.ClientSession instance has already been set')
        self._aiohttp_client_session = session

    def _build_client(self, name=None):
        url_path = self._url_path + [name] if name else self._url_path
        return AsyncClient(
            host=self.host,
            client_session=self.client_session,
            version=self._version,
            request_headers=self.request_headers,
            url_path=url_path,
            append_slash=self.append_slash,
            timeout=self.timeout)

    async def _make_request(self, request, timeout=None):
        if not self.client_session:
            raise AiohttpClientSessionError(
                'aiohttp.ClientSession instance is required')
        timeout = timeout or self.timeout
        try:
            async with self.client_session.request(
                request.get_method(),
                request.get_full_url(),
                headers={
                    key: str(value) for key, value in request.headers.items()
                },
                data=request.data,
                timeout=timeout,
            ) as response:
                code = response.status
                headers = response.headers
                body = await response.text()
                if code >= http.HTTPStatus.BAD_REQUEST:
                    raise HTTPError(
                        request.get_full_url(), code, body, headers, None)
        except ClientConnectionError as e:
            raise URLError(e.args[1].strerror)
        except HTTPError as e:
            raise handle_error(e)
        else:
            return AsyncResponse(code, body, headers)
