import asynctest
import sys
import pickle
import unittest
from collections import namedtuple

from aiohttp import ClientSession, web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from python_http_client.exceptions import BadRequestsError


if sys.version_info < (3, 5):
    raise unittest.SkipTest()

from python_http_client import (
    AiohttpClientSessionError,
    AsyncClient,
    Client,
)


class TestAsyncClientExceptionHandling(AioHTTPTestCase):
    async def get_application(self):
        async def handler(_):
            raise web.HTTPBadRequest(
                headers={'header': 'value'},
                reason='error_reason'
            )

        app = web.Application()
        app.router.add_get('/', handler)
        return app

    def get_url(self):
        server = self.server
        return '{}://{}:{}'.format(server.scheme, server.host, server.port)

    @unittest_run_loop
    async def test_error_handling(self):
        async with ClientSession() as session:
            client = AsyncClient(self.get_url(), client_session=session)
            with self.assertRaises(BadRequestsError) as context:
                await client.get()
            exception = context.exception
            self.assertEqual('400: error_reason', exception.body)
            self.assertIn('header', exception.headers)
            self.assertEqual('value', exception.headers['header'])


class TestAsyncClient(asynctest.TestCase):
    def setUp(self):
        self.host = 'http://api.test.com'

    def test___init__(self):
        client = AsyncClient(self.host, client_session='AIOHTTP_SESSION_STUB')

        self.assertIsInstance(client, AsyncClient)
        self.assertIsInstance(client, Client)

        self.assertEqual(client.host, self.host)
        self.assertEqual(client.client_session, 'AIOHTTP_SESSION_STUB')
        self.assertEqual(client.request_headers, {})
        self.assertIs(client.timeout, None)
        self.assertIsNone(client._version)
        self.assertEqual(client._url_path, [])
        self.assertIsNone(client.timeout)

        methods = {'delete', 'get', 'patch', 'post', 'put'}
        self.assertEqual(client.methods, methods)

    def test_client_session_is_set(self):
        client = AsyncClient(self.host)
        self.assertIsNone(client.client_session)
        client = AsyncClient(self.host, client_session='AIOHTTP_SESSION_STUB')
        self.assertEqual(client.client_session, 'AIOHTTP_SESSION_STUB')

    def test_set_client_session(self):
        client = AsyncClient(self.host)
        self.assertIsNone(client.client_session)
        client.client_session = 'AIOHTTP_SESSION_STUB'
        self.assertEqual(client.client_session, 'AIOHTTP_SESSION_STUB')
        with self.assertRaises(AiohttpClientSessionError):
            client.client_session = 'ANOTHER_CLIENT_SESSION'

    def test__build_client(self):
        original_client = AsyncClient(
            host=self.host,
            client_session='AIOHTTP_SESSION',
            version=1,
            append_slash=True,
            timeout=60)
        produced_client = original_client.path
        self.assertEqual(produced_client.host, self.host)
        self.assertEqual(produced_client.client_session, 'AIOHTTP_SESSION')
        self.assertDictEqual(produced_client.request_headers, {})
        self.assertEqual(produced_client._version, 1)
        self.assertListEqual(produced_client._url_path, ['path'])
        self.assertEqual(produced_client.append_slash, True)

    def test_client_pickle_unpickle(self):
        client = AsyncClient(self.host, 'AIOHTTP_SESSION')
        pickled_client = pickle.dumps(client)
        unpickled_client = pickle.loads(pickled_client)
        self.assertDictEqual(
            client.__dict__,
            unpickled_client.__dict__,
            "original client and unpickled client must have the same state")

    async def test__make_request(self):
        async def response_text():
            return 'response-text'

        server_response = asynctest.Mock()
        server_response.status = 200
        server_response.headers = {
            'Response-Header': 'response-header-content'
        }
        server_response.text.return_value = response_text()

        request_context_manager = asynctest.MagicMock()
        request_context_manager.__aenter__.return_value = server_response

        session = asynctest.Mock()
        session.request.return_value = request_context_manager

        request = namedtuple(
            'Request',
            ['get_method', 'get_full_url', 'headers', 'data']
        )(
            lambda: 'get',
            lambda: 'http://example.com',
            {'Header': 'header-content'},
            'request-data')

        client = AsyncClient(self.host)

        with self.assertRaises(AiohttpClientSessionError):
            await client._make_request(request)

        client.client_session = session
        response = await client._make_request(request)
        session.request.assert_called_once_with(
            'get',
            'http://example.com',
            data='request-data',
            headers={'Header': 'header-content'},
            timeout=None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, 'response-text')
        self.assertDictEqual(
            response.headers, {'Response-Header': 'response-header-content'})
