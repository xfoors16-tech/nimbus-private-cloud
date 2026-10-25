from io import BytesIO, StringIO

from a2wsgi import ASGIMiddleware

from app.main import app


def test_fastapi_health_route_works_through_wsgi_adapter():
    response = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api/v1/health",
        "QUERY_STRING": "",
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(),
        "wsgi.errors": StringIO(),
        "wsgi.multithread": True,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    def start_response(status, headers, exc_info=None):
        response["status"] = status
        response["headers"] = dict(headers)

    body = b"".join(ASGIMiddleware(app)(environ, start_response))

    assert response["status"] == "200 OK"
    assert response["headers"]["content-type"].startswith("application/json")
    assert b'"status":"ok"' in body
