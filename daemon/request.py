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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict
import base64

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = {}
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return (None, None, None)

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        # Handle case where path extraction failed
        if self.path is None:
            print("[Request] ERROR: Failed to extract path from request")
            self.headers = {}
            return
        
        #
        # @bksysnet Preapring the webapp hook with WeApRous instance
        # The default behaviour with HTTP server is empty routed
        #
        # TODO manage the webapp hook in this mounting point
        #
        
        original_path = self.path

        # Split path and query string for route matching
        if '?' in self.path:
            route_path, query_string = self.path.split('?', 1)
        else:
            route_path = self.path
            query_string = ''

        if routes:
            self.routes = routes
            # Look up route using path WITHOUT query parameters
            self.hook = routes.get((self.method, route_path))
            
            if not self.hook:
                print(f"[Request] No route found for {self.method} {route_path}")

        self.headers = self.prepare_headers(request)

        # Store the original full path in headers so handlers can access query params
        self.headers['path'] = original_path
                    #
            # self.hook manipulation goes here
            # ...
            #
        cookies = self.headers.get('cookie', '')
            #
            #  TODO: implement the cookie function here
            #        by parsing the header            #

        if cookies:
            for pair in cookies.split(';'):
                stripped_pair = pair.strip()
                if '=' in stripped_pair:
                    key, value = stripped_pair.split('=', 1)
                    self.cookies[key] = value

        return

    def prepare_body(self, data, files, json=None):
        body = None
        if data:
            body = data
        elif json:
            body = json
        if body:
            self.body = body
            self.prepare_content_length(self.body)
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        if hasattr(self, 'auth') and self.auth:
            self.prepare_auth(self.auth)
        return


    def prepare_content_length(self, body):
        length = 0
        if self.body:
            length = len(self.body)
        self.headers["Content-Length"] = str(length)
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return


    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        if isinstance(auth, tuple) and len(auth) == 2:
            username, password = auth
            auth_string = f"{username}:{password}"

            encoded_bytes = base64.b64encode(auth_string.encode('latin1')) 
            encoded_auth = encoded_bytes.decode('latin1')

            self.headers['Authorization'] = f"Basic {encoded_auth}"
        
        if url:
            self.url

        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies
