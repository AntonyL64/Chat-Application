#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict
import base64
import json
import mimetypes
import socket

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Read request header and body robustly (respect Content-Length)
        data = b""
        # First, read until headers end
        try:
            conn.settimeout(1.0)
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            # Proceed with whatever we have
            pass

        header_bytes = data
        body_bytes = b""
        if b"\r\n\r\n" in data:
            header_bytes, body_bytes = data.split(b"\r\n\r\n", 1)

        # Parse headers to find Content-Length
        try:
            header_text = header_bytes.decode('utf-8', errors='ignore')
        except Exception:
            header_text = ''

        # Build a simple headers dict
        headers = {}
        header_lines = header_text.split('\r\n')
        for line in header_lines[1:]:
            if ': ' in line:
                k, v = line.split(': ', 1)
                headers[k.lower()] = v

        content_length = int(headers.get('content-length', '0')) if headers.get('content-length') else 0

        # If we haven't read full body yet, read remaining bytes
        remaining = content_length - len(body_bytes)
        try:
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining))
                if not chunk:
                    break
                body_bytes += chunk
                remaining -= len(chunk)
        except socket.timeout:
            pass

        # Prepare msg as decoded header + separator + body string
        try:
            body_str = body_bytes.decode('utf-8', errors='ignore') if body_bytes else None
        except Exception:
            body_str = None

        msg = header_text + '\r\n\r\n' + (body_str or '')
        req.prepare(msg, routes)

        # Check if request preparation failed
        if req.path is None or req.method is None:
            print(f"[HttpAdapter] Request preparation failed - invalid request")
            resp.status_code = 400
            resp.reason = "Bad Request"
            resp._content = b"<h1>400 Bad Request</h1>"
            try:
                header_bytes = (f"HTTP/1.1 400 Bad Request\r\n"
                               f"Content-Type: text/html\r\n"
                               f"Content-Length: {len(resp._content)}\r\n\r\n").encode('utf-8')
                conn.sendall(header_bytes + resp._content)
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return None

        # Ensure request body and headers available to hooks
        req.body = body_str
        req.headers = headers  # keep lowercase keys

        # Normalize path and method
        path = getattr(req, "url", None) or getattr(req, "path", None) or "/"
        if not path.startswith("/"):
            path = "/" + path
        # prefer already-parsed method else derive from headers/first line
        method = (getattr(req, "method", None) or headers.get("method") or "GET").upper()

        print(f"[HttpAdapter] Processing request: {method} {path}")

        # Try to find the best matching handler in routes
        handler = None
        method_allowed_for_path = False  # True if path exists but method differs

        try:
            # Debug: show request and routes shape
            try:
                if isinstance(routes, dict):
                    print(f"[HttpAdapter] trying to match route for ({method}, {path}) against routes keys: {list(routes.keys())}")
                else:
                    print(f"[HttpAdapter] trying to match route for ({method}, {path}) against routes type: {type(routes)}")
            except Exception:
                pass

            if isinstance(routes, dict):
                # 1) direct (METHOD, PATH)
                handler = routes.get((method, path))
                if handler:
                    print(f"[HttpAdapter] matched by (METHOD, PATH)")
                else:
                    # 2) Path-only: check path key (legacy)
                    if path in routes:
                        potential = routes.get(path)
                        if callable(potential):
                            handler = potential
                            print(f"[HttpAdapter] matched by PATH-only key")
                    # 3) check for any other methods registered for same path
                    if not handler:
                        # scan for keys that match the path but with different method
                        for k in routes.keys():
                            try:
                                if isinstance(k, (list, tuple)) and len(k) >= 2:
                                    if k[1] == path and k[0].upper() != method:
                                        method_allowed_for_path = True
                                        break
                                elif isinstance(k, str):
                                    # string key like "GET /path" or "POST:/path"
                                    upk = k.strip().upper()
                                    if upk.endswith(" " + path.upper()) or upk.endswith(":" + path):
                                        # extract method part before space/colon
                                        km = upk.split(" ", 1)[0].split(":")[0]
                                        if km != method:
                                            method_allowed_for_path = True
                                            break
                            except Exception:
                                continue

                # 4) also accept reversed tuple (PATH, METHOD) stored cases
                if not handler and (path, method) in routes:
                    handler = routes.get((path, method))
                    if handler:
                        print(f"[HttpAdapter] matched by (PATH, METHOD) tuple")

            # 5) If routes is list/tuple of pairs
            if not handler and isinstance(routes, (list, tuple)):
                for item in routes:
                    try:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            key = item[0]
                            val = item[1]
                            if key == (method, path) or key == path:
                                handler = val
                                print(f"[HttpAdapter] matched in list/tuple routes by key {key}")
                                break
                            # detect path-only entries with different methods
                            if key == path:
                                # if stored as tuple (method,path) elsewhere, check other entries
                                pass
                    except Exception:
                        continue

            # 6) Map index variants (allow / -> /index.html)
            if not handler:
                variants = [path]
                if path == "/":
                    variants += ["/index.html", "/index.htm"]
                else:
                    if path.endswith("index.html") or path.endswith("index.htm"):
                        variants += ["/"]
                for v in variants:
                    if isinstance(routes, dict) and (method, v) in routes:
                        handler = routes[(method, v)]
                        print(f"[HttpAdapter] matched by variant (METHOD, PATH) {(method, v)}")
                        break
                    if isinstance(routes, dict) and v in routes and callable(routes[v]):
                        handler = routes[v]
                        print(f"[HttpAdapter] matched by variant PATH {v}")
                        break

            # Assign handler if found
            if handler and callable(handler):
                req.hook = handler
                print(f"[HttpAdapter] fallback: route handler found for {path} -> {getattr(handler,'__name__', handler)}")
            else:
                # If a handler for the path exists but for a different method, return 405
                if method_allowed_for_path:
                    resp.status_code = 405
                    resp.reason = "Method Not Allowed"
                    resp._content = b"<h1>405 Method Not Allowed</h1>"
                    print(f"[HttpAdapter] path {path} exists but method {method} not allowed -> 405")
                else:
                    # No handler found for path at all
                    print(f"[HttpAdapter] fallback: no handler found for ({method}, {path})")
                    # leave req.hook as None so rest of code returns 404 later
        except Exception as e:
            print(f"[HttpAdapter] route-finder exception: {e}")
        # --- END REPLACEMENT ---


        # populate body on the request object so app hooks receive it
        req.body = body_str
        req.headers = headers  # ensure headers available

        # If a previous step set a non-200 status (e.g., 405), send it now
        if getattr(resp, "status_code", None) == 405:
            # Build and send the 405 response immediately
            try:
                header_bytes = resp.build_response_header(req)
            except Exception:
                status_line = f"HTTP/1.1 {getattr(resp, 'status_code', 405)} {getattr(resp, 'reason', 'Method Not Allowed')}\r\n"
                ct = resp.headers.get("Content-Type", "text/plain")
                clen = len(getattr(resp, "_content", b"") or b"")
                header_bytes = (status_line + f"Content-Type: {ct}\r\nContent-Length: {clen}\r\n\r\n").encode("utf-8")
            body_bytes = getattr(resp, "_content", b"") or b""
            full = header_bytes + (body_bytes if isinstance(body_bytes, (bytes, bytearray)) else str(body_bytes).encode("utf-8"))
            try:
                conn.sendall(full)
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return full

        # Call the route hook only if it's callable. Handle exceptions from the hook and missing handlers.
        app_response_data = None
        hook = getattr(req, "hook", None)

        if callable(hook):
            # Debug information (optional)
            try:
                route_path = getattr(hook, "_route_path", None)
                route_methods = getattr(hook, "_route_methods", None)
                print(f"[HttpAdapter] hook in route-path METHOD {route_methods} PATH {route_path}")
            except Exception:
                pass

            # Ensure the full path with query string is available in headers
            if hasattr(req, 'path') and req.path:
                req.headers['path'] = req.path
                print(f"[HttpAdapter] Added path to headers: {req.path}")

            try:
                app_response_data = hook(headers=req.headers, body=req.body)
            except Exception as e:
                # If the handler itself crashed, return 500
                print(f"[HttpAdapter] Exception in route hook: {e}")
                resp.status_code = 500
                resp.reason = "Internal Server Error"
                resp._content = (f"<h1>500 Internal Server Error</h1><pre>{e}</pre>").encode("utf-8")
        else:
            # No callable hook found → 404 Not Found (leave resp._content set by earlier code if any)
            print(f"[HttpAdapter] No callable route hook for request path {getattr(req, 'url', getattr(req, 'path', '<unknown>'))}")
            resp.status_code = 404
            resp.reason = "Not Found"
            resp._content = b"<h1>404 Not Found</h1>"

        if isinstance(app_response_data, dict):
            # If the app returned an explicit content blob (binary or bytes)
            if "_content" in app_response_data:
                resp._content = app_response_data["_content"]
                resp.headers["Content-Type"] = app_response_data.get("_mime", "application/octet-stream")
                resp.status_code = int(app_response_data.get("_status", 200))
                resp.reason = "OK"
            else:
                # Otherwise the dict is JSON-serializable; return JSON
                content = json.dumps(app_response_data).encode("utf-8")
                resp._content = content
                resp.headers["Content-Type"] = "application/json"
                resp.status_code = 200
                resp.reason = "OK"

            # Support both key names "_set_cookie" and "set_cookie"
            cookie_val = None
            try:
                cookie_val = app_response_data.get("_set_cookie") or app_response_data.get("set_cookie")
            except Exception:
                cookie_val = None
            if cookie_val:
                # Set the header so it is sent to client
                resp.headers["Set-Cookie"] = cookie_val


        elif isinstance(app_response_data, (bytes, bytearray)):
            resp._content = app_response_data
            resp.headers["Content-Type"] = "application/octet-stream"
            resp.status_code = 200
            resp.reason = "OK"

        elif isinstance(app_response_data, str):
            if "." in app_response_data and not app_response_data.strip().startswith("<"):
                mime = mimetypes.guess_type(app_response_data)[0] or "text/plain"
                with open(app_response_data, "rb") as f:
                    resp._content = f.read()
                resp.headers["Content-Type"] = mime
            else:
                resp._content = app_response_data.encode()
                resp.headers["Content-Type"] = "text/plain"
            resp.status_code = 200
            resp.reason = "OK"

        else:
            resp._content = b""
            resp.status_code = 200
            resp.reason = "OK"

        # Build and send HTTP response bytes from prepared resp and req.
        # The Response.build_response method is tuned for static file serving
        # and may return 404 for app routes (non-file paths). Instead, construct
        # headers from resp and send resp._content directly.
        try:
            header_bytes = resp.build_response_header(req)
        except Exception:
            # Fallback: build a minimal header
            status_line = f"HTTP/1.1 {getattr(resp, 'status_code', 200)} {getattr(resp, 'reason', 'OK')}\r\n"
            ct = resp.headers.get('Content-Type', 'application/json')
            clen = len(getattr(resp, '_content', b''))
            header_bytes = (status_line + f"Content-Type: {ct}\r\nContent-Length: {clen}\r\n\r\n").encode('utf-8')

        body_bytes = getattr(resp, '_content', b'') or b''
        full = header_bytes + (body_bytes if isinstance(body_bytes, (bytes, bytearray)) else str(body_bytes).encode('utf-8'))
        conn.sendall(full)
        conn.close()
        return full

    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}

        headers = getattr(req, "headers", {})
        cookie_header = headers.get("Cookie") or headers.get("cookie")
        if cookie_header:
            for pair in cookie_header.split(";"):
                if "=" in pair:
                    k, v = pair.strip().split("=", 1)
                    cookies[k] = v
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.status_code = getattr(resp, "status_code", 200)
        response.reason = getattr(resp, "reason", "OK")
        response.headers = getattr(resp, "headers", {})
        response._content = getattr(resp, "_content", b"")
        response.encoding = getattr(resp, "encoding", "utf-8")

        # URL normalization
        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8", errors="ignore")
        else:
            response.url = req.url

        # Attach cookies (from request headers)
        response.cookies = self.extract_cookies(req, resp)

        # Attach context
        response.request = req
        response.connection = self
        response.raw = resp  # store raw object for debugging

        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            auth_string = f"{username}:{password}"
            encoded_bytes = base64.b64encode(auth_string.encode('latin1')) 
            encoded_auth = encoded_bytes.decode('latin1')
            headers["Proxy-Authorization"] = f"Basic {encoded_auth}"

        return headers