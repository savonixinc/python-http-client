from collections import namedtuple
import http
from urllib.error import URLError, HTTPError

from aiohttp.client_exceptions import ClientConnectionError

from .client import Client, Response
from .exceptions import handle_error


class AsyncClient(Client):
    def __init__(
        self,
        host,
        aiohttp_session,
        request_headers=None,
        version=None,
        url_path=None,
        append_slash=False,
        timeout=None,
    ):
        super().__init__(
            host=host,
            request_headers=request_headers,
            version=version,
            url_path=url_path,
            append_slash=append_slash,
            timeout=timeout,
        )
        self._aiohttp_client_session = aiohttp_session

    def _build_client(self, name=None):
        url_path = self._url_path + [name] if name else self._url_path
        return AsyncClient(
            host=self.host,
            aiohttp_session=self._aiohttp_client_session,
            version=self._version,
            request_headers=self.request_headers,
            url_path=url_path,
            append_slash=self.append_slash,
            timeout=self.timeout,
        )

    async def _make_request(self, request, timeout=None):
        timeout = timeout or self.timeout
        try:
            async with self._aiohttp_client_session.request(
                request.get_method(),
                request.get_full_url(),
                headers=request.headers,
                data=request.data,
                timeout=timeout,
            ) as response:
                code = response.status
                headers = response.headers
                body = await response.text()
                if code > http.HTTPStatus.BAD_REQUEST:
                    raise HTTPError(
                        request.get_full_url(), code, body, headers, None
                    )
        except ClientConnectionError as e:
            raise URLError(e.args[1].strerror)
        except HTTPError as e:
            raise handle_error(e)
        else:
            response_class = namedtuple(
                "Response", ["getcode", "read", "info"],
            )(lambda: code, lambda: body, lambda: headers)
            return Response(response_class)