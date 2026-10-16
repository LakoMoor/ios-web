#!/usr/bin/env python3
"""Assemble real AArch64 programs for resident and paged RAM verification."""
from pathlib import Path
import subprocess
import tempfile

project = Path(__file__).resolve().parent.parent
out = project / 'web/runtime'
out.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    obj = str(Path(tmp) / 'probe.o')
    for paged, name in [(0, 'probe.bin'), (1, 'probe-paged.bin')]:
        subprocess.run(['aarch64-linux-gnu-as', '--defsym', f'PAGED={paged}',
                        '-o', obj, str(project / 'build/probe.S')], check=True)
        subprocess.run(['aarch64-linux-gnu-objcopy', '-O', 'binary',
                        '-j', '.text', obj, str(out / name)], check=True)
