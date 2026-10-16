#!/usr/bin/env bash
set -euxo pipefail
mkdir -p "$TARGET"
download() { curl --fail --retry 3 --connect-timeout 20 -L "$1" -o "$2"; }
build_zlib() {
download https://zlib.net/fossils/zlib-1.3.1.tar.gz zlib.tar.gz
tar xf zlib.tar.gz
pushd zlib-1.3.1
emconfigure ./configure --prefix="$TARGET" --static
emmake make -j4 install
popd


}
build_ffi() {
if [ ! -d ffi-3.4.8/.git ]; then
  git clone --depth=1 --branch v3.4.8 https://github.com/libffi/libffi.git ffi-3.4.8
fi
pushd ffi-3.4.8
git checkout 6a99edb8082f75e523e0d6ebaba42218b80e10c8
autoreconf -fiv
emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$TARGET" --enable-static --disable-shared --disable-dependency-tracking --disable-builddir --disable-multi-os-directory --disable-raw-api --disable-structs --disable-docs
emmake make -j4 install SUBDIRS=include
popd


}
build_glib() {
download https://download.gnome.org/sources/glib/2.75/glib-2.75.0.tar.xz glib.tar.xz
tar xf glib.tar.xz
python3 - <<'PY'
from pathlib import Path
p = Path('glib-2.75.0/glib/gconvert.c')
s = p.read_text()
old = 'return iconv (cd, inbuf, inbytes_left, outbuf, outbytes_left);'
new = '''size_t in_left = inbytes_left ? *inbytes_left : 0;
  size_t out_left = outbytes_left ? *outbytes_left : 0;
  size_t result = iconv (cd, inbuf, inbytes_left ? &in_left : NULL,
                        outbuf, outbytes_left ? &out_left : NULL);
  if (inbytes_left) *inbytes_left = in_left;
  if (outbytes_left) *outbytes_left = out_left;
  return result;'''
if old not in s:
    raise SystemExit('GLib iconv patch anchor missing')
p.write_text(s.replace(old, new, 1))
PY
printf '#include <netdb.h>\nint res_query(const char*n,int c,int t,unsigned char*d,int l){h_errno=HOST_NOT_FOUND;return -1;}\n' > resolv.c
emcc $CFLAGS -c resolv.c -o resolv.o
emar rcs "$TARGET/lib/libresolv.a" resolv.o
meson setup --reconfigure glib-build glib-2.75.0 --cross-file=/deps/cross.ini --prefix="$TARGET" --default-library=static --buildtype=release --force-fallback-for=pcre2,gvdb -Dselinux=disabled -Dxattr=false -Dlibmount=disabled -Dnls=disabled -Dtests=false -Dglib_assert=false -Dglib_checks=false
sed -i -E '/#define HAVE_(CLOSE_RANGE|EPOLL_CREATE|KQUEUE|POSIX_SPAWN|FALLOCATE) 1/d' glib-build/config.h
meson install -C glib-build


}
build_pixman() {
download https://cairographics.org/releases/pixman-0.42.2.tar.gz pixman.tar.gz
tar xf pixman.tar.gz
pushd pixman-0.42.2
emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$TARGET" --disable-shared --enable-static --disable-gtk --disable-libpng --disable-openmp --disable-arm-simd --disable-arm-neon --disable-vmx --disable-mmx --disable-sse2 --disable-ssse3
emmake make -j4 install
popd


}
build_gmp() {
download https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz gmp.tar.xz
tar xf gmp.tar.xz
pushd gmp-6.3.0
ABI=standard emconfigure ./configure --host=none --prefix="$TARGET" --disable-assembly --disable-shared --enable-static
emmake make -j4 install
popd


}
build_nettle() {
download https://ftp.gnu.org/gnu/nettle/nettle-3.10.2.tar.gz nettle.tar.gz
echo 'fe9ff51cb1f2abb5e65a6b8c10a92da0ab5ab6eaf26e7fc2b675c45f1fb519b5 nettle.tar.gz' | sha256sum -c -
tar xf nettle.tar.gz
pushd nettle-3.10.2
emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$TARGET" --disable-assembler --disable-shared --enable-static --disable-documentation
emmake make -j4 install
popd


}
build_tasn1() {
download https://ftp.gnu.org/gnu/libtasn1/libtasn1-4.20.0.tar.gz tasn1.tar.gz
tar xf tasn1.tar.gz
pushd libtasn1-4.20.0
emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$TARGET" --disable-shared --enable-static --disable-doc --disable-tools ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes
emmake make -j4 install
popd


}
build_lzfse() {
download https://github.com/lzfse/lzfse/archive/refs/tags/lzfse-1.0.tar.gz lzfse.tar.gz
tar xf lzfse.tar.gz
emcmake cmake -S lzfse-lzfse-1.0 -B lzfse-build -DCMAKE_INSTALL_PREFIX="$TARGET" -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build lzfse-build -j4
cmake --install lzfse-build

}
build_png() {
download https://download.sourceforge.net/libpng/libpng-1.6.50.tar.xz png.tar.xz
tar xf png.tar.xz
pushd libpng-1.6.50
emconfigure ./configure --host=wasm32-unknown-emscripten --prefix="$TARGET" --disable-shared --enable-static
emmake make -j4 install
popd
}
case "${1:-all}" in
png) build_png ;;
zlib) build_zlib ;;
ffi) build_ffi ;;
glib) build_glib ;;
pixman) build_pixman ;;
gmp) build_gmp ;;
nettle) build_nettle ;;
tasn1) build_tasn1 ;;
lzfse) build_lzfse ;;
all) build_zlib; build_ffi; build_glib; build_pixman; build_gmp; build_nettle; build_tasn1; build_lzfse; build_png ;;
*) exit 2 ;;
esac
