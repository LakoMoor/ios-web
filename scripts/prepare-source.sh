#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
commit=cc4302a99167abec69b714cfd00c38caece7e7de
if [ ! -d vendor/inferno/.git ]; then
  mkdir -p vendor
  git clone https://github.com/ChefKissInc/Inferno.git --no-checkout --filter=blob:none vendor/inferno
fi
git -C vendor/inferno fetch --depth=1 origin "$commit"
git -C vendor/inferno checkout --detach "$commit"
git -C vendor/inferno submodule update --init --depth=1 util/mlib
