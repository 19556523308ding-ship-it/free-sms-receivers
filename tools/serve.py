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


def _strip_en(p):
    """英文版 /en/xxx -> (/en, /xxx)；非英文 -> ('', p)"""
    if p == "/en" or p == "/en/":
        return "/en", "/"
    if p.startswith("/en/"):
        return "/en", p[3:]
    return "", p


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _resolve(self, p, q):
        """把干净 URL 映射成实际文件路径（支持 /en/ 前缀）。"""
        prefix, rest = _strip_en(p)
        sub = os.path.join(ROOT, prefix.lstrip("/")) if prefix else ROOT

        if rest in SIMPLE:
            return prefix + SIMPLE[rest] + (("?" + q) if q else "")
        if rest == "/":
            return prefix + "/index.html"
        if rest.startswith("/country/"):
            seg = rest[len("/country/"):].strip("/")
            if seg and "/" not in seg:
                # 英文版优先取 /en/country/<iso>.html，回落 /en/country.html?c=
                static = os.path.join(sub, "country", seg.lower() + ".html")
                if os.path.isfile(static):
                    return f"{prefix}/country/{seg.lower()}.html"
                return f"{prefix}/country.html?c=" + urllib.parse.quote(seg)
        if rest.startswith("/number/"):
            nid = rest[len("/number/"):]
            return f"{prefix}/number.html?id=" + urllib.parse.quote(nid)
        return self.path

    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        self.path = self._resolve(parts.path, parts.query)
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
