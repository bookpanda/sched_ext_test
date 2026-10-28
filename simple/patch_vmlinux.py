"""Add Linux 7.1 sched_ext_ops fields missing from a 7.0 vmlinux.h.

SCX_OPS_OPEN in the 7.1 headers refers to sub_attach, sub_detach, and
sub_cgroup_id. Those members are only present in the skeleton when the
BPF object was compiled against a struct that has them. The running
kernel's BTF does not, so copy its vmlinux.h and insert the fields where
7.1 placed them. A vmlinux.h that already has them is copied unchanged.
"""

import pathlib
import sys


def main() -> None:
    src, dst = sys.argv[1:]
    text = pathlib.Path(src).read_text()
    if "(*sub_attach)" not in text:
        ops = (
            "\tvoid (*cgroup_set_idle)(struct cgroup *, bool);\n"
            "\tvoid (*cpu_online)(s32);"
        )
        ops_new = (
            "\tvoid (*cgroup_set_idle)(struct cgroup *, bool);\n"
            "\ts32 (*sub_attach)(struct scx_sub_attach_args *);\n"
            "\tvoid (*sub_detach)(struct scx_sub_detach_args *);\n"
            "\tvoid (*cpu_online)(s32);"
        )
        tail = "\tu64 hotplug_seq;\n\tchar name[128];"
        tail_new = "\tu64 hotplug_seq;\n\tu64 sub_cgroup_id;\n\tchar name[128];"
        if ops not in text or tail not in text:
            raise SystemExit(
                "vmlinux.h sched_ext_ops layout is not the expected 7.0 shape"
            )
        text = text.replace(ops, ops_new, 1).replace(tail, tail_new, 1)
        text = text.replace(
            "struct sched_ext_ops {",
            "struct scx_sub_attach_args;\n"
            "struct scx_sub_detach_args;\n"
            "\n"
            "struct sched_ext_ops {",
            1,
        )
    pathlib.Path(dst).write_text(text)


if __name__ == "__main__":
    main()
