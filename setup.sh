#!/bin/bash

root=$(cd "$(dirname "$0")" && pwd)

sudo apt update

sudo apt install -y \
  stress-ng \
  linux-tools-common \
  linux-tools-generic \
  bpftrace \
  bpftop \
  build-essential \
  git \
  clang \
  llvm \
  libelf-dev \
  libbpf-dev \
  pkg-config \
  linux-headers-$(uname -r) \
  sysstat \
  time \
  python3-venv

python3 -m venv "$root/.venv"
"$root/.venv/bin/pip" install matplotlib

cd "$root/.."
git clone https://github.com/masoncl/schbench.git
cd schbench
make
./schbench --help