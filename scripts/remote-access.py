#!/usr/bin/env python3
"""Authorized Jupyter terminal access; credentials arrive on hidden stdin only."""
import sys, json, termios, urllib.request, urllib.parse, http.cookiejar, re, os, time, socket
from websockets.sync.client import connect, ClientConnection
from websockets.exceptions import InvalidStatus

if sys.stdin.isatty():
    settings = termios.tcgetattr(sys.stdin)
    settings[3] &= ~termios.ECHO
    termios.tcsetattr(sys.stdin, termios.TCSANOW, settings)
print('Ready for connection JSON on stdin (input hidden).', flush=True)
config=json.loads(sys.stdin.readline())
base=config['url'].rstrip('/')
jar=http.cookiejar.CookieJar()
http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def request(path, body=None, method=None):
    data=None;headers={}
    if body is not None:
        data=json.dumps(body).encode();headers['Content-Type']='application/json'
    xsrf=next((c.value for c in jar if c.name=='_xsrf'),None)
    if xsrf: headers['X-XSRFToken']=xsrf
    with http.open(urllib.request.Request(base+path,data=data,headers=headers,method=method),timeout=30) as response:
        content=response.read()
        return json.loads(content) if response.headers.get('Content-Type','').startswith('application/json') else content.decode()

login=request('/login?next=%2Flab')
xsrf=next((c.value for c in jar if c.name=='_xsrf'),None)
payload=urllib.parse.urlencode({'password':config.pop('password'),'_xsrf':xsrf or ''}).encode()
with http.open(urllib.request.Request(base+'/login?next=%2Flab',data=payload),timeout=25) as response:
    page=response.read()
del payload, login, page
try:
    terminals=request('/api/terminals')
except urllib.error.HTTPError as error:
    print('Authentication/API failed: HTTP '+str(error.code),flush=True);sys.exit(1)
if config.get('mode')=='rest':
    print('Authenticated; REST command mode ready (input hidden).',flush=True)
    for line in sys.stdin:
        action=json.loads(line)
        if action.get('close'):break
        if 'mkdir' in action:
            request('/api/contents/'+urllib.parse.quote(action['mkdir'],safe='/'),{'type':'directory'},'PUT')
            print('Created task directory.',flush=True)
        elif 'write' in action:
            request('/api/contents/'+urllib.parse.quote(action['write'],safe='/'),{'type':'file','format':'text','content':action['content']},'PUT')
            print('Wrote task configuration.',flush=True)
        elif 'upload' in action:
            import base64
            with open(action['upload'],'rb') as f: content=base64.b64encode(f.read()).decode()
            request('/api/contents/'+urllib.parse.quote(action['path'],safe='/'),{'type':'file','format':'base64','content':content},'PUT')
            print('Uploaded '+action['path'],flush=True)
        elif 'run' in action:
            result=request('/api/terminals',{'cwd':action['cwd'],'shell_command':action['run']},'POST')
            print('Started task process; terminal '+result['name'],flush=True)
        elif 'read' in action:
            try:
                data=request('/api/contents/'+urllib.parse.quote(action['read'],safe='/')+'?content=1')
                content=data.get('content','')
                if data.get('format')=='base64':
                    import base64
                    content=base64.b64decode(content).decode()
                print(content,flush=True)
            except urllib.error.HTTPError as error:print('Task result HTTP '+str(error.code),flush=True)
    sys.exit(0)
terminal=request('/api/terminals',{},'POST')['name']
print('Authenticated; created task terminal.',flush=True)
cookie='; '.join(c.name+'='+c.value for c in jar)
uri=base.replace('https://','wss://').replace('http://','ws://')+'/terminals/websocket/'+urllib.parse.quote(terminal)
try:
    # Forward plain HTTP Upgrade through the configured sidecar proxy. A
    # CONNECT tunnel for plaintext WS isn't accepted by this HTTP proxy.
    connect_options={}
    configured_proxy=urllib.request.getproxies().get('http')
    if uri.startswith('ws://') and configured_proxy:
        proxy_address=urllib.parse.urlsplit(configured_proxy)
        proxy_socket=socket.create_connection((proxy_address.hostname,proxy_address.port or 80),timeout=20)
        def forward_connection(sock,protocol,**kwargs):
            original=protocol.connect
            def forward_request():
                req=original();req.path=base+req.path;return req
            protocol.connect=forward_request
            return ClientConnection(sock,protocol,**kwargs)
        connect_options={'sock':proxy_socket,'proxy':None,'create_connection':forward_connection}
    with connect(uri,origin=base,additional_headers={'Cookie':cookie},open_timeout=20,max_size=8*1024*1024,**connect_options) as ws:
        ws.send(json.dumps(['stdin',"stty -echo\nprintf '\\n__REMOTE_READY__\\n'\n"]))
        output=''
        while '__REMOTE_READY__' not in output:
            message=json.loads(ws.recv(timeout=20))
            if message[0]=='stdout':output+=message[1]
        print('Remote terminal ready. Send JSON lines: {"command":"..."} or {"upload":"local.zip","path":"remote.zip"}.',flush=True)
        for line in sys.stdin:
            command=json.loads(line)
            if 'upload' in command:
                import base64
                with open(command['upload'],'rb') as f: content=base64.b64encode(f.read()).decode()
                request('/api/contents/'+urllib.parse.quote(command['path'],safe='/'),{'type':'file','format':'base64','content':content},'PUT')
                print('Uploaded '+command['path'],flush=True);continue
            if command.get('close'):
                break
            marker='__TASK_DONE_'+str(time.time_ns())+'__'
            text=command['command']+'\nprintf "\\n'+marker+'\\n"\n'
            ws.send(json.dumps(['stdin',text]));output=''
            while marker not in output:
                message=json.loads(ws.recv(timeout=command.get('timeout',60)))
                if message[0]=='stdout':
                    output+=message[1]
                    if len(output)>16*1024*1024:raise RuntimeError('Remote output exceeded limit')
            print(output.split(marker)[0],flush=True)
except InvalidStatus as error:
    response=error.response
    print('WebSocket rejected: HTTP '+str(response.status_code),flush=True)
    for name in ['Server','Content-Type','X-Denied-Reason']:
        if name in response.headers:print(name+': '+response.headers[name],flush=True)
    print(bytes(response.body).decode(errors='replace')[:1600],flush=True)
finally:
    request('/api/terminals/'+urllib.parse.quote(terminal),method='DELETE')
