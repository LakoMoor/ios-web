#!/usr/bin/env bash
set -euxo pipefail
export SSL_CERT_FILE=/run/build-ca.pem CURL_CA_BUNDLE=/run/build-ca.pem PIP_CERT=/run/build-ca.pem GIT_SSL_CAINFO=/run/build-ca.pem REQUESTS_CA_BUNDLE=/run/build-ca.pem NODE_EXTRA_CA_CERTS=/run/build-ca.pem
if [ ! -x /opt/build-tools/bin/meson ]; then
  apt-get -o Acquire::https::CaInfo=/run/build-ca.pem update
  apt-get -o Acquire::https::CaInfo=/run/build-ca.pem install -y autoconf automake libtool pkg-config ninja-build python3-pip python3-venv gettext texinfo bison flex libglib2.0-dev
  python3 -m venv /opt/build-tools
  /opt/build-tools/bin/pip install meson==1.9.0
fi
export PATH=/opt/build-tools/bin:$PATH
export TARGET=/opt/wasm CFLAGS='-O2 -pthread -matomics -mbulk-memory' CXXFLAGS='-O2 -pthread -matomics -mbulk-memory'
export LDFLAGS='-L/opt/wasm/lib -pthread' CPATH=/opt/wasm/include PKG_CONFIG_LIBDIR=/opt/wasm/lib/pkgconfig EM_PKG_CONFIG_PATH=/opt/wasm/lib/pkgconfig
mkdir -p /deps
cp /project/build/dependencies.sh /project/build/cross.ini /deps/
cd /deps
for dependency in zlib ffi glib pixman gmp nettle tasn1 lzfse png; do
  stamp="$dependency"
  if [ "$dependency" = ffi ]; then stamp=ffi-3.4.8; fi
  if [ "$dependency" = glib ]; then stamp=glib-sdk4; fi
  if [ ! -f "/deps/$stamp.done" ]; then
    bash /deps/dependencies.sh "$dependency"
    touch "/deps/$stamp.done"
  fi
done
git config --global --add safe.directory /project/vendor/inferno
git config --global --add safe.directory /project/vendor/inferno/util/mlib
git -C /project/vendor/inferno submodule update --init --depth=1 util/mlib
bash /project/build/compile.sh --resume
