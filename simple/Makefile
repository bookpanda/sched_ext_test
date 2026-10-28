# Build this out-of-tree scheduler against the course kernel's sched_ext headers.
LINUX_SRC ?= $(HOME)/code/linux
SCX_DIR := $(abspath $(LINUX_SRC))/tools/sched_ext
SCX_INC := $(SCX_DIR)/include
SCX_BUILD := $(SCX_DIR)/build
SCX_GENINC := $(SCX_BUILD)/include
VMLINUX_H := $(SCX_GENINC)/vmlinux.h
BPFTOOL := $(SCX_BUILD)/sbin/bpftool
LIBBPF := $(SCX_BUILD)/obj/libbpf/libbpf.a

ARCH := $(shell uname -m | sed 's/x86_64/x86/;s/aarch64/arm64/')
CLANG ?= clang
CC ?= gcc

OUT := build
BPF_OBJ := $(OUT)/scx_simple.bpf.o
SKEL := $(OUT)/scx_simple.bpf.skel.h
BIN := $(OUT)/scx_simple

SYS_INCLUDES := $(shell $(CLANG) -v -E - </dev/null 2>&1 \
	| sed -n '/<...> search starts here:/,/End of search list./{ s| \(/.*\)|-idirafter \1|p }')

BPF_CFLAGS := -g -O2 -target bpf -D__TARGET_ARCH_$(ARCH) -mlittle-endian \
	-I$(SCX_INC) -I$(SCX_INC)/bpf-compat -I$(SCX_GENINC) \
	-I$(LINUX_SRC)/tools/include/uapi -I$(LINUX_SRC)/include \
	$(SYS_INCLUDES) \
	-Wall -Wno-compare-distinct-pointer-types -Wno-microsoft-anon-tag \
	-fms-extensions -mcpu=v3

CFLAGS := -g -O2 -Wall -I$(SCX_INC) -I$(SCX_GENINC) -I$(OUT)
LDFLAGS := -lelf -lz -lpthread

.PHONY: all clean kernel-headers

all: $(BIN)

# One sched_ext build produces vmlinux.h, libbpf, and bpftool together.
kernel-headers:
	$(MAKE) -C $(SCX_DIR) $(VMLINUX_H)

$(BPF_OBJ): scx_simple.bpf.c | kernel-headers $(OUT)
	$(CLANG) $(BPF_CFLAGS) -c $< -o $@

$(SKEL): $(BPF_OBJ) | kernel-headers
	$(BPFTOOL) gen object $(OUT)/scx_simple.bpf.linked1.o $<
	$(BPFTOOL) gen object $(OUT)/scx_simple.bpf.linked2.o $(OUT)/scx_simple.bpf.linked1.o
	$(BPFTOOL) gen object $(OUT)/scx_simple.bpf.linked3.o $(OUT)/scx_simple.bpf.linked2.o
	$(BPFTOOL) gen skeleton $(OUT)/scx_simple.bpf.linked3.o name scx_simple > $@

$(BIN): scx_simple.c $(SKEL) | kernel-headers
	$(CC) $(CFLAGS) -o $@ scx_simple.c $(LIBBPF) $(LDFLAGS)

$(OUT):
	mkdir -p $(OUT)

clean:
	rm -rf $(OUT)
