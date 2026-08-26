"""
Netlify Serverless Function Handler for PulseCare Public Health Network
Handles URL path normalization, fallback WSGI execution, and error reporting.
"""
import sys
import os
import urllib.parse
import io

# Add project root directory to Python import path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ["NETLIFY"] = "true"

try:
    from app import app
except Exception as e:
    app = None
    import_error = str(e)
else:
    import_error = None

def fallback_wsgi_handler(event, context):
    """Native WSGI runner for Flask on AWS Lambda / Netlify Functions."""
    if app is None:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/html"},
            "body": f"<h3>PulseCare App Import Error</h3><pre>{import_error}</pre>"
        }

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    
    # Strip Netlify function prefix from path
    for prefix in ["/.netlify/functions/app", "/.netlify/functions/api"]:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if not path:
        path = "/"

    headers = event.get("headers", {}) or {}
    query_params = event.get("queryStringParameters", {}) or {}
    body = event.get("body", "") or ""

    qs = urllib.parse.urlencode(query_params)

    environ = {
        "REQUEST_METHOD": http_method,
        "PATH_INFO": path,
        "SCRIPT_NAME": "",
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

def handler(event, context):
    # Normalize event path
    path = event.get("path", "/")
    for prefix in ["/.netlify/functions/app", "/.netlify/functions/api"]:
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if not path:
        path = "/"
    event["path"] = path

    try:
        import serverless_wsgi
        if app is not None:
            return serverless_wsgi.handle_request(app, event, context)
        return fallback_wsgi_handler(event, context)
    except Exception:
        return fallback_wsgi_handler(event, context)
