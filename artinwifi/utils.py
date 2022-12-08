import logging
from urllib.parse import urlunparse

from scrapy import Request
from scrapy.exceptions import NotConfigured
from scrapy.http import Response
from scrapy.utils.httpobj import urlparse_cached
from scrapy.utils.python import to_bytes
from twisted.web import http

log = logging.getLogger(__name__)


class LoggingDownloaderMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings['REQUEST_RESPONSE_DEBUG']
        if not enabled:
            raise NotConfigured

        return cls()

    def process_request(self, request, spider):
        repr = request_httprepr(request, body=False)
        log.debug(f"Request:\n{repr}")
        return

    def process_response(self, request, response, spider):
        repr = response_httprepr(response, body=False)
        log.debug(f"Reponse:\n{repr}")
        return response


def response_httprepr(response: Response, body: bool = False) -> str:
    """Return raw HTTP representation (as bytes) of the given response. This
    is provided only for reference, since it's not the exact stream of bytes
    that was received (that's not exposed by Twisted).
    """
    values = [
        b"HTTP/1.1 ",
        to_bytes(str(response.status)),
        b" ",
        to_bytes(http.RESPONSES.get(response.status, b'')),
        b"\r\n",
    ]
    if response.headers:
        values.extend([response.headers.to_string(), b"\r\n"])
    if body:
        values.extend([b"\r\n", response.body])
    return b"".join(values).decode("utf-8")


def request_httprepr(request: Request, body: bool = False) -> str:
    """Return the raw HTTP representation (as bytes) of the given request.
    This is provided only for reference since it's not the actual stream of
    bytes that will be send when performing the request (that's controlled
    by Twisted).
    """
    parsed = urlparse_cached(request)
    path = urlunparse(('', '', parsed.path or '/', parsed.params, parsed.query, ''))
    s = to_bytes(request.method) + b" " + to_bytes(path) + b" HTTP/1.1\r\n"
    s += b"Host: " + to_bytes(parsed.hostname or b'') + b"\r\n"
    if request.headers:
        s += request.headers.to_string() + b"\r\n"
    s += b"\r\n"
    if body:
        s += request.body
    return s.decode("utf-8")
