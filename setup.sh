#!/bin/bash

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
  time