# syntax=docker/dockerfile:1
FROM emscripten/emsdk:4.0.15
ENV SSL_CERT_FILE=/run/build-ca.pem CURL_CA_BUNDLE=/run/build-ca.pem PIP_CERT=/run/build-ca.pem GIT_SSL_CAINFO=/run/build-ca.pem REQUESTS_CA_BUNDLE=/run/build-ca.pem NODE_EXTRA_CA_CERTS=/run/build-ca.pem
RUN --mount=type=secret,id=ca,target=/run/build-ca.pem,required=true \
    apt-get -o Acquire::https::CaInfo=/run/build-ca.pem update && \
    apt-get -o Acquire::https::CaInfo=/run/build-ca.pem install -y autoconf automake libtool pkg-config ninja-build python3-pip python3-venv gettext texinfo bison flex libglib2.0-dev binutils-aarch64-linux-gnu && \
    python3 -m venv /opt/build-tools && /opt/build-tools/bin/pip install meson==1.9.0
ENV PATH=/opt/build-tools/bin:$PATH
ENV TARGET=/opt/wasm CFLAGS="-O2 -pthread -matomics -mbulk-memory" CXXFLAGS="-O2 -pthread -matomics -mbulk-memory"
ENV LDFLAGS="-L/opt/wasm/lib -pthread" CPATH=/opt/wasm/include PKG_CONFIG_LIBDIR=/opt/wasm/lib/pkgconfig EM_PKG_CONFIG_PATH=/opt/wasm/lib/pkgconfig
WORKDIR /deps
COPY build/dependencies.sh build/cross.ini /deps/
RUN --mount=type=secret,id=ca,target=/run/build-ca.pem,required=true bash /deps/dependencies.sh all
WORKDIR /project
