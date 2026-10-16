#!/usr/bin/env python3
"""Static HTTP server. --pages simulates GitHub Pages without COOP/COEP headers."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse
import os
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=4173)
parser.add_argument('--pages',action='store_true')
args=parser.parse_args()
os.chdir(Path(__file__).resolve().parent.parent/'dist')
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm'}
    def do_GET(self):
        if self.path.startswith('/ios-web/'): self.path=self.path[len('/ios-web'):]
        super().do_GET()
    def do_HEAD(self):
        if self.path.startswith('/ios-web/'): self.path=self.path[len('/ios-web'):]
        super().do_HEAD()
    def end_headers(self):
        if not args.pages:
            self.send_header('Cross-Origin-Opener-Policy','same-origin')
            self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        self.send_header('Cache-Control','no-store')
        super().end_headers()
print(f'http://localhost:{args.port}/ios-web/ — Pages simulation: {args.pages}',flush=True)
ThreadingHTTPServer(('0.0.0.0',args.port),Handler).serve_forever()
