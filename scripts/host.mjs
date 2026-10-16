// SPDX-License-Identifier: AGPL-3.0-only
import http from 'node:http';
import https from 'node:https';
import {readFileSync,createReadStream,existsSync} from 'node:fs';
import {stat} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
import {scryptSync,timingSafeEqual,createHmac,randomBytes} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export function createHandler({root,credentials}) {
  root=resolve(root);
  const sessionKey=randomBytes(32);let acceptedDigest;
  const fingerprint=value=>createHmac('sha256',sessionKey).update(value).digest();
  function authorized(header) {
    if(typeof header!=='string'||!header.startsWith('Basic ')||header.length>1024)return false;
    const digest=fingerprint(header);
    if(acceptedDigest&&timingSafeEqual(digest,acceptedDigest))return true;
    let decoded;try{decoded=Buffer.from(header.slice(6),'base64').toString('utf8');}catch{return false;}
    const colon=decoded.indexOf(':');if(colon<0||decoded.slice(0,colon)!==credentials.username)return false;
    const key=scryptSync(decoded.slice(colon+1),Buffer.from(credentials.salt,'hex'),64);
    const expected=Buffer.from(credentials.key,'hex');
    if(key.length!==expected.length||!timingSafeEqual(key,expected))return false;
    acceptedDigest=digest;return true;
  }
  return async function handler(req,res) {
    res.setHeader('Cross-Origin-Opener-Policy','same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy','require-corp');
    res.setHeader('Cross-Origin-Resource-Policy','same-origin');
    res.setHeader('X-Content-Type-Options','nosniff');
    res.setHeader('Cache-Control','no-store');
    if(!authorized(req.headers.authorization)){
      res.writeHead(401,{'WWW-Authenticate':'Basic realm="iOS Web admin", charset="UTF-8"','Content-Type':'text/plain;charset=utf-8'});res.end('Authentication required');return;
    }
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{Allow:'GET, HEAD'});res.end();return;}
    let pathname;try{pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);}catch{res.writeHead(400);res.end();return;}
    if(pathname==='/admin'){
      res.setHeader('Content-Type','application/json');res.end(JSON.stringify({service:'ios-web',authenticated:true,runtime:existsSync(resolve(root,'runtime/inferno.mjs'))&&existsSync(resolve(root,'runtime/qemu-system-aarch64.wasm'))?'present':'not-built',iosBootVerified:false}));return;
    }
    if(pathname.includes('\0')||pathname.split('/').some(part=>part.startsWith('.'))){res.writeHead(403);res.end();return;}
    const target=resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
    if(!target.startsWith(root+sep)){res.writeHead(403);res.end();return;}
    try{
      const info=await stat(target);if(!info.isFile())throw new Error('Not a file');
      const mime={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.mjs':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.svg':'image/svg+xml','.json':'application/json','.wasm':'application/wasm','.png':'image/png'};
      res.writeHead(200,{'Content-Type':mime[extname(target)]||'application/octet-stream','Content-Length':info.size});
      if(req.method==='HEAD')res.end();else createReadStream(target).on('error',()=>res.destroy()).pipe(res);
    }catch{res.writeHead(404);res.end('Not found');}
  };
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(!process.env.ADMIN_CREDENTIAL_FILE)throw new Error('ADMIN_CREDENTIAL_FILE is required');
  const credentials=JSON.parse(readFileSync(process.env.ADMIN_CREDENTIAL_FILE,'utf8'));
  if(!credentials.username||!credentials.salt||!credentials.key)throw new Error('Invalid credential configuration');
  const handler=createHandler({root:process.env.STATIC_ROOT||'dist',credentials});
  const secure=process.env.TLS_CERT_FILE&&process.env.TLS_KEY_FILE;
  const server=secure?https.createServer({cert:readFileSync(process.env.TLS_CERT_FILE),key:readFileSync(process.env.TLS_KEY_FILE)},handler):http.createServer(handler);
  const port=Number(process.env.PORT||8080);
  server.listen(port,'0.0.0.0',()=>console.log('iOS Web listening on '+(secure?'https':'http')+'://0.0.0.0:'+port+' (authentication required)'));
}
