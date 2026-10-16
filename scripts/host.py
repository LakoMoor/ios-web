#!/usr/bin/env python3
"""Dependency-free private host, with optional trusted TLS certificate."""
import base64,hashlib,hmac,json,os,ssl
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
root=Path(os.environ.get('STATIC_ROOT','dist')).resolve()
credentials=json.loads(Path(os.environ['ADMIN_CREDENTIAL_FILE']).read_text())
salt=bytes.fromhex(credentials['salt']);expected=bytes.fromhex(credentials['key'])
session_key=os.urandom(32);accepted=None
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.wasm':'application/wasm','.mjs':'text/javascript'}
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(root),**kwargs)
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def authorized(self):
        global accepted
        header=self.headers.get('Authorization','')
        if not header.startswith('Basic ') or len(header)>1024:return False
        digest=hmac.digest(session_key,header.encode(),'sha256')
        if accepted and hmac.compare_digest(digest,accepted):return True
        try:
            user,password=base64.b64decode(header[6:]).decode().split(':',1)
            if user!=credentials['username']:return False
            key=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=64)
            if not hmac.compare_digest(key,expected):return False
        except (ValueError,UnicodeError):return False
        accepted=digest;return True
    def do_GET(self):
        if not self.authorized():
            self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="iOS Web admin", charset="UTF-8"');self.end_headers();return
        from urllib.parse import unquote,urlsplit
        path=unquote(urlsplit(self.path).path)
        if any(part.startswith('.') for part in path.split('/')):
            self.send_error(403);return
        if path=='/admin':
            body=json.dumps({'service':'ios-web','authenticated':True,'runtime':'present' if (root/'runtime/inferno.mjs').is_file() and (root/'runtime/qemu-system-aarch64.wasm').is_file() else 'not-built','iosBootVerified':False}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        super().do_GET()
    def do_HEAD(self):
        if not self.authorized():
            self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="iOS Web admin"');self.end_headers();return
        super().do_HEAD()
server=ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),Handler)
secure=bool(os.environ.get('TLS_CERT_FILE') and os.environ.get('TLS_KEY_FILE'))
if secure:
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(os.environ['TLS_CERT_FILE'],os.environ['TLS_KEY_FILE'])
    server.socket=context.wrap_socket(server.socket,server_side=True)
print('iOS Web host ready on port 8080; TLS='+str(secure)+'; authentication required',flush=True)
server.serve_forever()
