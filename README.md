# 百宝箱 · Android 版（Kivy）

桌面版「百宝箱」的安卓移植：登录 + 药品清单 + 费用组合匹配 + 组合日志 + 组合小工具。
核心逻辑（随机组合生成、匹配、SQLite 存储）复用桌面版纯 Python，UI 用 Kivy 重写。

## 功能
- **登录**：默认密码 `123456`，可修改。
- **药品清单**：首次启动自动灌入桌面版已导入的 18 条药品（`seed_medicines.json`），也可手动录入 / 删除（名称、规格、单位、单价、数量）。
- **费用组合**：输入目标金额，从药品中匹配合计接近的组合。
- **组合日志**：查看明细、编辑名称/备注、删除（二次确认）。
- **组合小工具**：输入姓名 / 每条金额上限 / 合计金额（自动算最少条数），随机生成组合，可复制 / 存日志。

## 本地运行（桌面调试）
```bash
pip install kivy
python main.py
# 仅跑逻辑自测（不启动 GUI）
python main.py --selftest
```

## 构建 APK（GitHub Actions 自动出包）
本仓库已配置 `.github/workflows/build.yml`：推送后自动在 Linux 上用 Buildozer 编译 debug APK 并上传为可下载产物。

步骤：
1. 在 GitHub 新建仓库，把本目录内容推送上去（含 `main.py` / `logic.py` / `store.py` / `selftest.py` / `buildozer.spec` / `icon.png` / `.github/`）。
   - 注意：`.gitignore` 已忽略 `.venv`、`bin/`、`.buildozer/`、`*.db`，请勿强行提交这些。
2. 进入仓库 **Actions → Build Android APK**，手动触发或推送 `main`/`master` 分支自动触发。
3. 构建完成后，在 **Artifacts** 下载 `baibao-android-apk`（内含 `Baibao-debug.apk`）。
4. 把 APK 传到手机 → 允许「未知来源」安装 → 安装。

> 首次构建会下载 Android SDK/NDK，约 15–30 分钟；之后有缓存会快些。

## 在手机上安装测试
- APK 为 **debug** 包，无需签名即可安装（需开启「设置 → 安全 → 未知来源应用」）。
- 默认密码 `123456`；首次进入后建议去登录页「修改密码」。
- 数据保存在 App 私有目录（`user_data_dir`），卸载即清空。

## 自定义
- 包名：改 `buildozer.spec` 的 `package.name` / `package.domain`（默认 `org.baibao` / `com.example.baibao`，上线前请改成你自己的）。
- 应用标题：`buildozer.spec` 的 `title`（当前英文 `Baibao`，中文标题在部分系统会显示为方框，故用英文）。
- 图标：`icon.png`（已生成纯绿底占位图，可替换为正式图标）。

## 与桌面版差异（v1）
- 手机端**导入数据改为手动录入**（桌面版从 Excel 导入；移动端文件权限较复杂，v1 暂未做 CSV/Excel 导入）。但桌面版已导入的 **18 条药品已导出为 `seed_medicines.json` 一并打进 APK**，App 首次启动且药品表为空时会自动灌入，等同于「已导入的数据随包携带」。
- 界面为 Kivy 移动风格，非桌面窗口风格。
- 组合小工具仅支持**整数金额**（每条上限 / 合计金额按整数处理，不保留小数），与桌面版一致。
- 其余逻辑（随机组合、匹配、日志、复制文本）与桌面版一致。
