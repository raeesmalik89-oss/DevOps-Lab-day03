#!/usr/bin/env python3

import http.server
import json
import os
import signal
import socketserver
import sys

PORT = int(os.environ.get("PORT", "8080"))
VERSION = os.environ.get("APP_VERSION", "0.0.0")


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/health":
            body = {
                "status": "healthy",
                "version": VERSION
            }

        elif self.path == "/crash":
            print("crash requested", flush=True)
            sys.exit(1)

        else:
            body = {
                "message": "hello from systemd",
                "version": VERSION
            }

        payload = json.dumps(body).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "Content-Length",
            str(len(payload))
        )
        self.end_headers()

        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(
            "%s - %s" % (
                self.address_string(),
                fmt % args
            ),
            flush=True
        )


def shutdown(signum, frame):
    print(
        f"signal {signum} received, shutting down cleanly",
        flush=True
    )
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

print(
    f"starting on port {PORT}, version {VERSION}",
    flush=True
)

socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
