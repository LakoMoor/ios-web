#!/usr/bin/env python3
"""A real AArch64 UART program, not a JS simulation. Loaded by QEMU loader."""
from pathlib import Path
import struct
out = Path(__file__).resolve().parent.parent / 'web/runtime'
out.mkdir(parents=True, exist_ok=True)
# x1=PL011 UART (0x09000000); x0=message; print bytes; then wfe forever.
words = [
    0xD2A12001,  # movz x1,#0x900,lsl#16
    0x100000E0,  # adr x0, message (offset 28)
    0x38401402,  # ldrb w2,[x0],#1
    0x34000062,  # cbz w2, done (+12)
    0x39000022,  # strb w2,[x1]
    0x17FFFFFD,  # b loop (-12)
    0xD503205F,  # wfe
    0x17FFFFFF,  # b done (-4)
]
message = b'\r\nINFERNO_WASM_ARM64_OK\r\nAArch64 guest executed on TCI / WebAssembly.\r\n\0'
(out / 'probe.bin').write_bytes(struct.pack('<8I', *words) + message)
