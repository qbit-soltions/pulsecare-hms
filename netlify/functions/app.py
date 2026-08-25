"""
Netlify Serverless Function Handler for PulseCare Hospital Management System
"""
import sys
import os

# Add root directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Set Netlify environment flag
os.environ["NETLIFY"] = "true"

from app import app

try:
    import serverless_wsgi
    def handler(event, context):
        return serverless_wsgi.handle_request(app, event, context)
except ImportError:
    import urllib.parse
    import io

    def handler(event, context):
        """Fallback lightweight WSGI adapter for AWS Lambda / Netlify Functions."""
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        headers = event.get("headers", {})
        query_string = event.get("queryStringParameters", {}) or {}
        body = event.get("body", "") or ""
        
        # Build query string
        qs = urllib.parse.urlencode(query_string)

        environ = {
            "REQUEST_METHOD": http_method,
            "PATH_INFO": path,
            "QUERY_STRING": qs,
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "443",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "https",
            "wsgi.input": io.BytesIO(body.encode("utf-8") if isinstance(body, str) else body),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        for key, value in headers.items():
            key = key.upper().replace("-", "_")
            if key in ["CONTENT_TYPE", "CONTENT_LENGTH"]:
                environ[key] = value
            else:
                environ[f"HTTP_{key}"] = value

        response_headers = []
        response_status = [200]

        def start_response(status, response_headers_list, exc_info=None):
            response_status[0] = int(status.split(" ")[0])
            response_headers.extend(response_headers_list)

        result = app(environ, start_response)
        response_body = b"".join(result)

        headers_dict = {k: v for k, v in response_headers}
        return {
            "statusCode": response_status[0],
            "headers": headers_dict,
            "body": response_body.decode("utf-8", errors="replace"),
            "isBase64Encoded": False
        }
