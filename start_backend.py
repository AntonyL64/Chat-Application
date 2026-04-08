#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_backend
~~~~~~~~~~~~~~~~~

This module provides a simple entry point for deploying backend server process
using the socket framework. It parses command-line arguments to configure the
server's IP address and port, and then launches the backend server.
"""

import socket
import argparse

from daemon import create_backend

import start_sampleapp  # <<< ensures decorators run

def main():
    ip = '0.0.0.0'
    port = 9000

    # pull routes registered by app.route(...)
    routes = start_sampleapp.app.routes

    # print("[start_backend] Loaded routes:", list(routes.keys()))

    create_backend(ip, port, routes=routes)

if __name__ == "__main__":
    """
    Entry point for launching the backend server.

    This block parses command-line arguments to determine the server's IP address
    and port. It then calls `create_backend(ip, port)` to start the RESTful
    application server.

    :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
    :arg --server-port (int): Port number to bind the server (default: 9000).
    """

    main()
