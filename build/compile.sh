#!/usr/bin/env bash
set -euxo pipefail
cd /project
python3 build/patch.py vendor/inferno
mkdir -p build-output/qemu web/runtime
cd build-output/qemu
emconfigure /project/vendor/inferno/configure --cc=emcc --cxx=em++ --ar=emar --ranlib=emranlib --nm=emnm --strip=emstrip \
  --cpu=wasm32 --cross-prefix= --target-list=aarch64-softmmu \
  --without-default-features --without-default-devices --with-devices-aarch64=browser \
  --enable-system --enable-tcg --enable-tcg-interpreter --enable-pixman --enable-png --enable-lzfse --enable-nettle \
  --enable-fdt --disable-tools --disable-guest-agent --disable-docs --disable-werror --disable-stack-protector \
  --with-coroutine=wasm --extra-cflags='-O2 -pthread -matomics -mbulk-memory -Wno-error=incompatible-function-pointer-types -Wno-error=incompatible-pointer-types -I/opt/wasm/include' \
  --extra-ldflags='-L/opt/wasm/lib'
ninja -j4 qemu-system-aarch64
cp qemu-system-aarch64 /project/web/runtime/inferno.mjs
cp qemu-system-aarch64.wasm /project/web/runtime/
# Emscripten 4 embeds its pthread worker in the ES module; older toolchains may emit it.
find . -maxdepth 1 -name 'qemu-system-aarch64*.worker*' -exec cp '{}' /project/web/runtime/ \;
python3 /project/scripts/make-probe.py
python3 /project/scripts/runtime-manifest.py
