#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地预览服务器：模拟线上 nginx 的干净 URL 规则。
- /country/us          -> /country/us.html（静态页优先）
- /country/xx 无静态页  -> /country.html?c=xx（回落动态页）
- /numbers /guide /faq /admin -> 对应 .html
- /                    -> index.html
用法：python tools/serve.py [port]
"""
import os
import sys
import http.server
import socketserver
import urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "web")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899

SIMPLE = {"/numbers": "/numbers.html", "/guide": "/guide.html",
          "/faq": "/faq.html", "/admin": "/admin.html"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        p, q = parts.path, parts.query

        # 1) 无扩展名页面 -> 补 .html
        if p in SIMPLE:
            self.path = SIMPLE[p] + (("?" + q) if q else "")
        elif p == "/":
            self.path = "/index.html"
        elif p.startswith("/country/"):
            seg = p[len("/country/"):].strip("/")
            if seg and "/" not in seg:
                static = os.path.join(ROOT, "country", seg.lower() + ".html")
                if os.path.isfile(static):
                    self.path = f"/country/{seg.lower()}.html"
                else:
                    self.path = "/country.html?c=" + urllib.parse.quote(seg)
        super().do_GET()

    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"本地预览：http://127.0.0.1:{PORT}/  (root={ROOT})")
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        httpd.serve_forever()
