#! /usr/bin/env python3
# coding=utf-8
"""Fake application web server"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from subprocess import run, PIPE, STDOUT


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Server that test FPGA presence"""

    def do_GET(self):
        """GET"""
        process = run(['/opt/xilinx/xrt/bin/awssak', 'list'],
                      stderr=STDOUT, stdout=PIPE)
        self.send_response(500 if process.returncode else 200)
        self.end_headers()
        self.wfile.write(process.stdout)


HTTPServer(('0.0.0.0', 8080), SimpleHTTPRequestHandler).serve_forever()
