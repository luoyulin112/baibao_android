#!/usr/bin/env python3
"""
Patch python-for-android 解压后的 python3 3.11.9 源码中的 Modules/grpmodule.c，
把 grp_getgrall_impl 里的 setgrent() / getgrent() / endgrent() 调用用 #if 0 包起来，
跳过对 Android Bionic libc 不存在的 POSIX groups 迭代 API。

为什么需要：cpython 3.11.9 grpmodule.c 的 grp_getgrall_impl 函数体没有 #ifdef 包裹
setgrent/getgrent/endgrent。configure 时 AC_CHECK_FUNCS 在 Android NDK sysroot 中误判
（grp.h stub 声明存在）→ 编译时 -Werror=implicit-function-declaration 直接失败。
我们的 App 不使用 grp 模块，禁掉整个函数体对功能无影响。

用法：在 build.yml 中每次 python -m buildozer 跑前调用一次本脚本（patch 已 patch
过的文件是 no-op，幂等）。
"""

import glob
import os
import sys


def patch_one(path: str) -> bool:
    """对一个 grpmodule.c 做幂等 patch，返回是否真正修改过。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if "grp disabled for Android" in src:
        # 已 patch
        return False

    # 锚点 1：setgrent(); 前面加 #if 0
    anchor_open = "        return NULL;\n    setgrent();"
    replacement_open = (
        "        return NULL;\n"
        "#if 0  /* grp disabled for Android: Bionic libc lacks "
        "setgrent/getgrent/endgrent */\n"
        "    setgrent();"
    )
    if anchor_open not in src:
        # 文件不是预期的 3.11.x 结构，跳过
        return False
    new_src = src.replace(anchor_open, replacement_open, 1)

    # 锚点 2：在末尾 endgrent();\n    return d;\n} 之后插入 #endif
    anchor_close = "    endgrent();\n    return d;\n}"
    replacement_close = "    endgrent();\n#endif\n    return d;\n}"
    if anchor_close not in new_src:
        return False
    new_src = new_src.replace(anchor_close, replacement_close, 1)

    if new_src == src:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    return True


def main() -> int:
    base = os.path.expanduser(os.environ.get("BUILDOZER_HOME", "~/.buildozer"))
    patched = 0
    candidates = glob.glob(
        os.path.join(base, "**", "Modules", "grpmodule.c"), recursive=True
    )
    for path in candidates:
        if patch_one(path):
            print(f"[patch_grpmodule] patched: {path}", flush=True)
            patched += 1
    print(f"[patch_grpmodule] total patched: {patched}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())