#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
root = Path(__file__).resolve().parent.parent / 'web/runtime'
files = {p.name: {'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in root.iterdir() if p.is_file() and p.name not in ('manifest.json', '.gitkeep')}
(root / 'manifest.json').write_text(json.dumps({'upstream':'ChefKissInc/Inferno','commit':'cc4302a99167abec69b714cfd00c38caece7e7de','files':files}, indent=2) + '\n')
