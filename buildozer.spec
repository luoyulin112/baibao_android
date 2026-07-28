[app]

# (str) 应用版本（buildozer 强制要求，缺失会直接报错退出）
version = 1.0.0

# (str) 应用标题（中文会在部分系统显示为方框，建议用拼音/英文标题；桌面端显示名另算）
title = Baibao
# (str) 包名（必须唯一，反向域名风格）
package.name = com.example.baibao
package.domain = org.baibao

# (str) 入口源码（buildozer 会把整个目录打包进 APK，main.py 即入口）
source.dir = .
source.include_exts = py,png,jpg,kv,json
source.exclude_exts = spec,db
source.exclude_dirs = .venv,__pycache__,tests

# (list) 应用要求（python3 + kivy）
requirements = hostpython3==3.11.9, python3==3.11.9, kivy==2.3.1

# (str) 应用主类（Kivy App 类名，buildozer 会自动找 main.py 里的 App）
# 不填时 buildozer 默认加载 main.py 中第一个 App 子类

# (str) 图标（放在工程根目录）
icon.filename = icon.png

# (str) 竖屏
orientation = portrait

# (list) 权限（v1 不读写外部存储，仅需网络可选，这里留空即可）
android.permissions =

# (int) Android API
android.api = 34
android.minapi = 24
android.ndk = 25b
android.build_tools_version = 34.0.0

# CI 编译必须自动接受 SDK 许可协议（否则 buildozer 在干净 Linux 上会卡住报错）
android.accept_licenses = True

# 本地 p4a recipes：编译 python3 前 patch grpmodule.c，跳过 Android Bionic libc
# 不支持的 setgrent/getgrent/endgrent（cpython 3.11.9 函数体未 #ifdef 包裹）。
# buildozer 把 requirements.source.<X> 转成 P4A_X_DIR 环境变量传给 p4a，加载本地 recipe
# 覆盖默认的同名 recipe。注意：必须放在 [app] 段下，且值为 recipe 目录路径
# （不是文件路径），目录里需要包含 __init__.py。
requirements.source.python3 = p4a_recipes/python3

# (bool) 是否显示启动图
android.private_storage = True
android.start_service = False

# (str) 输出 apk 名
# buildozer 默认输出 bin/<title>-<version>-debug.apk

[buildozer]

# (int) 日志级别
log_level = 2

# (str) buildozer 缓存目录
build_dir = .buildozer

# (bool) 是否清理过期构建
# CI 上每次都是全新虚拟机，设为 False 避免反复重新下载 SDK/NDK（更快更稳）
android.clean_build = False
