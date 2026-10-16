import os,sys,json,shutil,socket
from pathlib import Path
result={'cwd':os.getcwd(),'python':sys.version.split()[0],'uid':os.getuid(),
        'tools':{name:shutil.which(name) for name in ['node','npm','docker','nginx','caddy','certbot','systemctl','gcc','make']},
        'diskFreeGiB':round(shutil.disk_usage('.').free/2**30,2),
        'trustedCertAvailable':Path('/etc/letsencrypt/live/lakomoor.com/fullchain.pem').is_file() and Path('/etc/letsencrypt/live/lakomoor.com/privkey.pem').is_file()}
sock=socket.socket()
try:sock.bind(('0.0.0.0',8080));result['port8080Free']=True
except OSError:result['port8080Free']=False
finally:sock.close()
Path('inspection.json').write_text(json.dumps(result,indent=2))
