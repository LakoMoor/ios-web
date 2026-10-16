#!/usr/bin/env python3
"""Assemble real AArch64 programs for resident and paged RAM verification."""
from pathlib import Path
import subprocess
import struct
import sys
import tempfile

project = Path(__file__).resolve().parent.parent
out = project / 'web/runtime'
out.mkdir(parents=True, exist_ok=True)
if '--wrap-existing' not in sys.argv:
    with tempfile.TemporaryDirectory() as tmp:
        obj = str(Path(tmp) / 'probe.o')
        for paged, name in [(0, 'probe.bin'), (1, 'probe-paged.bin')]:
            subprocess.run(['aarch64-linux-gnu-as', '--defsym', f'PAGED={paged}',
                            '-o', obj, str(project / 'build/probe.S')], check=True)
            subprocess.run(['aarch64-linux-gnu-objcopy', '-O', 'binary',
                            '-j', '.text', obj, str(out / name)], check=True)
# One standard ELF64 PT_LOAD segment. QEMU's ARM kernel loader uses its
# 64-bit physical address and entry point directly; no extra loader device.
for name, entry in [('probe', 0x40080000), ('probe-paged', 0x100080000)]:
    code = (out / (name + '.bin')).read_bytes()
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 183, 1, entry,
                         64, 0, 0, 64, 56, 1, 0, 0, 0)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 4096, entry, entry,
                          len(code), len(code), 4096)
    (out / (name + '.elf')).write_bytes((header + segment).ljust(4096, b'\0') + code)
