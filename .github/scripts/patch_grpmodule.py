#!/usr/bin/env python3
"""
Patch p4a 解压后的 cpython 3.11.9 源码中的 Modules/grpmodule.c，
把 grp_getgrall_impl 里的 setgrent() / getgrent() / endgrent() 调用用 #if 0 包起来，
跳过对 Android Bionic libc 不存在的 POSIX groups 迭代 API。

为什么需要：cpython 3.11.9 grpmodule.c 的 grp_getgrall_impl 函数体没有 #ifdef 包裹
setgrent/getgrent/endgrent。configure 时 AC_CHECK_FUNCS 在 Android NDK sysroot 中误判
（grp.h stub 声明存在）→ 编译时 -Werror=implicit-function-declaration 直接失败。
我们的 App 不使用 grp 模块，禁掉整个函数体对功能无影响。

调用时机：必须等 p4a 把 cpython 3.11.9 源码解压到
~/.buildozer/android/platform/build-<arch>/build/other_builds/python3/<arch>/python3/Modules/grpmodule.c
之后再跑（即 buildozer 第一次跑完之后）。脚本本身幂等。

用法：在 build.yml 的 Build APK 步，buildozer 第一次跑后、第二次跑前调用。
"""

import glob
import os
import sys


# 与 p4a_recipes/python3/__init__.py 保持一致的锚点
_ANCHOR_OPEN = "        return NULL;\n    setgrent();"
_REPLACEMENT_OPEN = (
    "        return NULL;\n"
    "#if 0  /* grp disabled for Android: Bionic libc lacks "
    "setgrent/getgrent/endgrent */\n"
    "    setgrent();"
)
_ANCHOR_CLOSE = "    endgrent();\n    return d;\n}"
_REPLACEMENT_CLOSE = "    endgrent();\n#endif\n    return d;\n}"
_MARKER = "grp disabled for Android"


def patch_one(path: str) -> bool:
    """对一个 grpmodule.c 做幂等 patch，返回是否真正修改过。"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    if _MARKER in src:
        return False

    if _ANCHOR_OPEN not in src or _ANCHOR_CLOSE not in src:
        return False

    new_src = src.replace(_ANCHOR_OPEN, _REPLACEMENT_OPEN, 1).replace(
        _ANCHOR_CLOSE, _REPLACEMENT_CLOSE, 1
    )
    if new_src == src:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    return True


def main() -> int:
    base = os.path.expanduser(
        os.environ.get("BUILDOZER_HOME", "~/.buildozer")
    )
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