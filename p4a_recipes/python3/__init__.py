# p4a local_recipes / python3 hook
# 在 p4a 解压 python3 源码后、编译 Modules 前 patch grpmodule.c，
# 跳过 setgrent/getgrent/endgrent（Android Bionic libc 未实现这些 POSIX groups 迭代 API）。
# 详见 buildozer.spec 的 android.p4a.local_recipes 配置。

from pythonforandroid.recipes.python3 import Python3Recipe as _Base
from pythonforandroid.logger import info

# 与 build.yml 中 patch_grpmodule.py 保持一致的锚点
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


class Python3Recipe(_Base):
    name = "python3"

    def prebuild_arch(self, arch):
        # 调用父类，让 p4a 完成 download + unpack + 标准 patches
        super().prebuild_arch(arch)

        # 此时 grpmodule.c 已解压，在 patch_modules 前手动 patch 一次
        try:
            grp_path = self.get_build_dir(arch.arch) + "/Modules/grpmodule.c"
        except Exception:
            return
        import os

        if not os.path.exists(grp_path):
            info("grpmodule.c not found at {}; skipping patch".format(grp_path))
            return

        with open(grp_path, "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
        if _MARKER in src:
            info("grpmodule.c already patched")
            return
        if _ANCHOR_OPEN not in src or _ANCHOR_CLOSE not in src:
            info(
                "grpmodule.c anchors not found (Python version mismatch?); "
                "skipping patch"
            )
            return

        new_src = src.replace(_ANCHOR_OPEN, _REPLACEMENT_OPEN, 1).replace(
            _ANCHOR_CLOSE, _REPLACEMENT_CLOSE, 1
        )
        with open(grp_path, "w", encoding="utf-8") as f:
            f.write(new_src)
        info("patched grpmodule.c at {} (grp module disabled)".format(grp_path))


recipe = Python3Recipe()