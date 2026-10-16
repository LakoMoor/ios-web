#!/usr/bin/env python3
import base64,json,sys,termios,urllib.request,urllib.error
if sys.stdin.isatty():
    settings=termios.tcgetattr(sys.stdin);settings[3]&=~termios.ECHO
    termios.tcsetattr(sys.stdin,termios.TCSANOW,settings)
print('Ready for verification JSON on stdin (input hidden).',flush=True)
config=json.loads(sys.stdin.readline())
base=config['url'].rstrip('/')
header='Basic '+base64.b64encode((config['username']+':'+config.pop('password')).encode()).decode()
results=[]
def fetch(path,auth=False):
    request=urllib.request.Request(base+path,headers={'Authorization':header} if auth else {})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            body=response.read();status=response.status;headers=response.headers
    except urllib.error.HTTPError as error:
        body=error.read();status=error.code;headers=error.headers
    results.append({'path':path,'authenticated':auth,'status':status,'coop':headers.get('Cross-Origin-Opener-Policy'),'coep':headers.get('Cross-Origin-Embedder-Policy')})
    return status,body
try:
    status,_=fetch('/')
    assert status==401,'Anonymous access must be denied'
    status,body=fetch('/',True);assert status==200,'Authenticated page must be accessible'
    assert 'iOS / Web' in body.decode()
    for path in ['/app.js','/style.css','/config.js','/emulator-worker.js','/swap-storage-worker.js']:
        status,_=fetch(path,True);assert status==200,path
    status,body=fetch('/admin',True);assert status==200
    service=json.loads(body)
    status,_=fetch('/runtime/manifest.json',True)
    print(json.dumps({'verified':True,'url':base+'/','checks':results,'service':service,'runtimeManifestStatus':status},indent=2),flush=True)
except Exception as error:
    print(json.dumps({'verified':False,'url':base+'/','error':str(error),'checks':results},indent=2),flush=True)
    sys.exit(1)
