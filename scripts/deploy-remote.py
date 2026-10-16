#!/usr/bin/env python3
"""Install into the new task directory; never replace a listener on port 8080."""
import json,os,shutil,socket,subprocess,sys,time,zipfile
from pathlib import Path
task=Path.cwd().resolve()
result={}
try:
    probe=socket.socket()
    try:probe.bind(('0.0.0.0',8080))
    finally:probe.close()
    destination=task/'project';destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(task/'ios-web-source.zip') as archive:
        for name in archive.namelist():
            path=(destination/name).resolve()
            if not path.is_relative_to(destination):raise ValueError('Unsafe archive member')
        archive.extractall(destination)
    project=destination/'ios-web'
    shutil.copytree(project/'web',project/'dist',dirs_exist_ok=True)
    (project/'dist/.nojekyll').touch()
    credential_file=task/'admin-8080.json'
    credential_file.chmod(0o600)
    env=os.environ.copy()
    env.update({'PORT':'8080','STATIC_ROOT':str(project/'dist'),'ADMIN_CREDENTIAL_FILE':str(credential_file)})
    cert=Path('/etc/letsencrypt/live/lakomoor.com/fullchain.pem')
    key=Path('/etc/letsencrypt/live/lakomoor.com/privkey.pem')
    secure=cert.is_file() and key.is_file() and os.access(cert,os.R_OK) and os.access(key,os.R_OK)
    if secure:env.update({'TLS_CERT_FILE':str(cert),'TLS_KEY_FILE':str(key)})
    node=shutil.which('node')
    command=[node,str(project/'scripts/host.mjs')] if node else [sys.executable,'-u',str(project/'scripts/host.py')]
    with (task/'host.log').open('ab') as log:
        child=subprocess.Popen(command,cwd=project,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (task/'host.pid').write_text(str(child.pid))
    for _ in range(40):
        if child.poll() is not None:raise RuntimeError('Host exited: '+(task/'host.log').read_text()[-1500:])
        try:
            with socket.create_connection(('127.0.0.1',8080),timeout=.25):break
        except OSError:time.sleep(.25)
    else:raise RuntimeError('Host failed to open port 8080')
    result={'started':True,'pid':child.pid,'url':('https' if secure else 'http')+'://lakomoor.com:8080/','username':'admin','tls':secure,'runtime':'not-built','iosBootVerified':False,'project':str(project),'log':str(task/'host.log')}
except Exception as error:result={'started':False,'error':str(error)}
(task/'deployment.json').write_text(json.dumps(result,indent=2))
