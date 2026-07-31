"""百宝箱 · Android 版（Kivy）。

四大板块（与桌面版一致）：
  1. 药品清单   —— 手动录入 / 删除
  2. 费用组合   —— 输入目标金额，从药品中匹配接近的组合
  3. 组合日志   —— 查看明细、编辑名称/备注、删除
  4. 组合小工具 —— 按 姓名/每条上限/合计金额 随机生成费用组合，可复制 / 存日志

运行：python main.py            （桌面/手机调试）
     python main.py --selftest  （仅跑逻辑自测，不启动 GUI）
"""

import os
import sys
import json

import logic
import store
import traceback

# 顶层异常捕获：把未捕获异常的完整 traceback 写到 crash.txt，
# 便于在 Android 上闪退时从手机文件取回错误（无需 adb）。
# 会依次尝试脚本目录、当前工作目录，任一可写即写入。
def _install_crash_logger():
    def _hook(exc_type, exc_val, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        for cand in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
            try:
                with open(os.path.join(cand, "crash.txt"), "w", encoding="utf-8") as f:
                    f.write(tb)
                break
            except Exception:
                continue
        try:
            sys.__excepthook__(exc_type, exc_val, exc_tb)
        except Exception:
            pass
    sys.excepthook = _hook

_install_crash_logger()

# 在导入 kivy 之前处理 --selftest（kivy 会在 import 时读取 sys.argv，
# 否则 --selftest 会被 kivy 的命令行解析拦截）
if "--selftest" in sys.argv:
    import selftest
    selftest.run()
    print("SELFTEST_DONE")
    sys.exit(0)

from kivy.app import App
from kivy.lang import Builder
from kivy.core.clipboard import Clipboard
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.spinner import Spinner
from kivy.properties import ObjectProperty, StringProperty

# ---------------- 配色 ----------------
C_BG = "#f4f6f9"
C_PANEL = "#ffffff"
C_PRIMARY = "#149e5a"
C_PRIMARY_D = "#0f8048"
C_TEXT = "#22303f"
C_MUTED = "#7a8694"
C_BORDER = "#e4e9f0"
C_ERROR = "#c0392b"


# ---------------- 简易配置（密码） ----------------
CONFIG_DIR = None  # 由 App.build 设置（Android: user_data_dir）
DEFAULT_PWD = "123456"


def _pwd_path():
    return os.path.join(CONFIG_DIR, "password.json")


def load_password():
    p = _pwd_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f).get("password", DEFAULT_PWD)
        except Exception:
            pass
    return DEFAULT_PWD


def save_password(pwd):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(_pwd_path(), "w", encoding="utf-8") as f:
        json.dump({"password": pwd}, f, ensure_ascii=False)


# ---------------- 通用小工具 ----------------
def make_btn(text, on_press, bg=C_PRIMARY, color="#ffffff", size_hint=(None, None),
             width=120, height=42, font_size=15):
    b = Button(text=text, on_press=on_press, background_color=_rgb(bg),
               color=_rgb(color), size_hint=size_hint, width=width, height=height,
               font_size=font_size)
    return b


def _rgb(hexstr):
    hexstr = hexstr.lstrip("#")
    return tuple(int(hexstr[i:i + 2], 16) / 255 for i in (0, 2, 4))


def msg_popup(title, text):
    box = BoxLayout(orientation="vertical", padding=16, spacing=12)
    box.add_widget(Label(text=text, color=_rgb(C_TEXT), font_size=15,
                         text_size=(360, None), halign="center"))
    ok = make_btn("确定", lambda inst: popup.dismiss(), width=100, height=40)
    box.add_widget(ok)
    popup = Popup(title=title, content=box, size_hint=(0.8, 0.5))
    popup.open()
    return popup


def confirm_popup(title, text, on_yes):
    box = BoxLayout(orientation="vertical", padding=16, spacing=12)
    box.add_widget(Label(text=text, color=_rgb(C_TEXT), font_size=15,
                         text_size=(360, None), halign="center"))
    row = BoxLayout(orientation="horizontal", spacing=12, size_hint=(1, None), height=44)
    no = make_btn("取消", lambda inst: popup.dismiss(), bg=C_MUTED, width=110, height=42)
    yes = make_btn("确定", lambda inst: (popup.dismiss(), on_yes()), bg=C_ERROR, width=110, height=42)
    row.add_widget(no)
    row.add_widget(yes)
    box.add_widget(row)
    popup = Popup(title=title, content=box, size_hint=(0.8, 0.55))
    popup.open()
    return popup


def text_input(hint, text="", password=False, multiline=False):
    ti = TextInput(hint_text=hint, text=text, password=password, multiline=multiline,
                   background_color=_rgb(C_PANEL), foreground_color=_rgb(C_TEXT),
                   font_size=15, padding=(10, 8), size_hint_y=None, height=42,
                   write_tab=False)
    return ti


# ---------------- 登录界面 ----------------
class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", padding=40, spacing=20)
        root.add_widget(Label(text="百宝箱", font_size=30, color=_rgb(C_PRIMARY),
                              size_hint_y=None, height=60))
        root.add_widget(Label(text="请输入密码", font_size=15, color=_rgb(C_MUTED),
                              size_hint_y=None, height=30))

        self.pwd = text_input("密码", password=True)
        self.pwd.bind(on_text_validate=lambda inst: self.do_unlock())
        root.add_widget(self.pwd)

        root.add_widget(make_btn("解锁", lambda inst: self.do_unlock(),
                                 size_hint=(1, None), height=46))
        root.add_widget(make_btn("修改密码", lambda inst: self.open_change(),
                                 bg=C_MUTED, size_hint=(1, None), height=42))

        self.status = Label(text="", font_size=13, color=_rgb(C_ERROR),
                            size_hint_y=None, height=24)
        root.add_widget(self.status)
        self.add_widget(root)

    def do_unlock(self):
        if self.pwd.text == load_password():
            self.status.text = ""
            self.manager.current = "main"
        else:
            self.status.text = "密码错误"

    def open_change(self):
        box = BoxLayout(orientation="vertical", padding=16, spacing=12)
        old = text_input("旧密码", password=True)
        new = text_input("新密码", password=True)
        again = text_input("再次输入", password=True)
        box.add_widget(old)
        box.add_widget(new)
        box.add_widget(again)

        def do_change(inst):
            if old.text != load_password():
                msg_popup("提示", "旧密码不正确")
                return
            if not new.text:
                msg_popup("提示", "新密码不能为空")
                return
            if new.text != again.text:
                msg_popup("提示", "两次输入不一致")
                return
            save_password(new.text)
            popup.dismiss()
            msg_popup("成功", "密码已修改")

        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=44)
        row.add_widget(make_btn("取消", lambda inst: popup.dismiss(), bg=C_MUTED, width=120))
        row.add_widget(make_btn("保存", do_change, width=120))
        box.add_widget(row)
        popup = Popup(title="修改密码", content=box, size_hint=(0.9, 0.8))
        popup.open()


# ---------------- 主界面 ----------------
class MainScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        # 顶栏
        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=52,
                        padding=(12, 8), spacing=10)
        top.add_widget(Label(text="百宝箱", font_size=20, color=_rgb(C_PRIMARY),
                             size_hint_x=None, width=120))
        top.add_widget(Label(text="", size_hint_x=1))
        top.add_widget(make_btn("退出登录", lambda inst: self.logout(),
                                bg=C_MUTED, width=110, height=40, font_size=14))
        root.add_widget(top)

        # Tab 容器
        self.tabs = TabbedPanel(do_default_tab=False, tab_height=52,
                                background_color=_rgb(C_PANEL))
        root.add_widget(self.tabs)

        # 药品清单
        ti1 = TabbedPanelItem(text="药品清单", color=_rgb(C_TEXT), font_size=15)
        ti1.content = self._build_medicine_tab()
        self.tabs.add_widget(ti1)

        # 费用组合
        ti2 = TabbedPanelItem(text="费用组合", color=_rgb(C_TEXT), font_size=15)
        ti2.content = self._build_match_tab()
        self.tabs.add_widget(ti2)

        # 组合日志
        ti3 = TabbedPanelItem(text="组合日志", color=_rgb(C_TEXT), font_size=15)
        ti3.content = self._build_log_tab()
        self.tabs.add_widget(ti3)

        # 组合小工具
        ti4 = TabbedPanelItem(text="组合小工具", color=_rgb(C_TEXT), font_size=15)
        ti4.content = self._build_tool_tab()
        self.tabs.add_widget(ti4)

        # 默认显示第一个 Tab（药品清单）
        self.tabs.switch_to(ti1)

        self.add_widget(root)
        # 进入时刷新列表
        Clock_schedule_once(self.refresh_medicines, 0.1)
        # 注意：Clock.schedule_once 调用回调时会把 dt(0.1) 作为第一个参数传入，
        # 若直接传 self.refresh_logs 会变成 refresh_logs(0.1)（float），
        # 进而 store.fetch_logs 把 float 拼进字符串抛 TypeError 闪退。用 lambda 吞掉 dt。
        Clock_schedule_once(lambda dt: self.refresh_logs(""), 0.1)

    def logout(self):
        self.manager.current = "login"

    # ---- 药品清单 ----
    def _build_medicine_tab(self):
        self.med_list_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.med_list_box.bind(minimum_height=self.med_list_box.setter("height"))

        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(self.med_list_box)

        layout = BoxLayout(orientation="vertical", padding=12, spacing=10)
        form = GridLayout(cols=2, spacing=8, size_hint_y=None, height=200)
        self.m_name = text_input("名称")
        self.m_spec = text_input("规格")
        self.m_unit = text_input("单位")
        self.m_price = text_input("单价")
        self.m_count = text_input("数量")
        for w in (self.m_name, self.m_spec, self.m_unit, self.m_price, self.m_count):
            form.add_widget(w)
        layout.add_widget(form)
        layout.add_widget(make_btn("添加药品", lambda inst: self.add_medicine(),
                                   size_hint=(1, None), height=44))
        layout.add_widget(Label(text="药品列表", font_size=14, color=_rgb(C_MUTED),
                                size_hint_y=None, height=28))
        layout.add_widget(sv)
        return layout

    def add_medicine(self):
        name = self.m_name.text.strip()
        if not name:
            msg_popup("提示", "请填写名称")
            return
        try:
            price = float(self.m_price.text or 0)
            count = int(float(self.m_count.text or 0))
        except ValueError:
            msg_popup("提示", "单价/数量需为数字")
            return
        store.insert_medicine(name, self.m_spec.text.strip(), self.m_unit.text.strip(),
                              price, count)
        self.m_name.text = self.m_spec.text = self.m_unit.text = ""
        self.m_price.text = self.m_count.text = ""
        self.refresh_medicines()

    def refresh_medicines(self, *a):
        self.med_list_box.clear_widgets()
        for m in store.fetch_medicines():
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=44,
                            spacing=6)
            info = "{}  {}  单价{} x{} = {}".format(
                m["name"], m["spec"], logic.fmt_money(m["price"]),
                m["count"], logic.fmt_money(m["subtotal"]))
            row.add_widget(Label(text=info, color=_rgb(C_TEXT), font_size=13,
                                 text_size=(300, None), halign="left",
                                 size_hint_x=1))
            row.add_widget(make_btn("删", lambda inst, mid=m["id"]: self.del_medicine(mid),
                                    bg=C_ERROR, width=54, height=36, font_size=13))
            self.med_list_box.add_widget(row)

    def del_medicine(self, mid):
        confirm_popup("删除", "确定删除该药品？", lambda: (store.delete_medicine(mid),
                                                           self.refresh_medicines()))

    # ---- 费用组合 ----
    def _build_match_tab(self):
        self.match_result_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.match_result_box.bind(minimum_height=self.match_result_box.setter("height"))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(self.match_result_box)

        layout = BoxLayout(orientation="vertical", padding=12, spacing=10)
        self.target_in = text_input("目标金额")
        layout.add_widget(self.target_in)
        layout.add_widget(make_btn("找组合", lambda inst: self.do_match(),
                                   size_hint=(1, None), height=44))
        self.match_status = Label(text="从已录入药品中匹配接近目标金额的组合",
                                  font_size=13, color=_rgb(C_MUTED),
                                  size_hint_y=None, height=28)
        layout.add_widget(self.match_status)
        layout.add_widget(sv)
        return layout

    def do_match(self):
        try:
            target = float(self.target_in.text or 0)
        except ValueError:
            msg_popup("提示", "目标金额需为数字")
            return
        meds = store.fetch_medicines()
        results = logic.find_combos(meds, target, max_results=30)
        self.match_result_box.clear_widgets()
        if not results:
            self.match_status.text = "未找到匹配组合（请先录入药品）"
            return
        self.match_status.text = "共找到 %d 组" % len(results)
        for i, (sub, sub_total) in enumerate(results, 1):
            names = " + ".join(x["name"] for x in sub)
            row = Label(text="[%d] %s\n合计 %s" % (i, names, logic.fmt_money(sub_total)),
                        color=_rgb(C_TEXT), font_size=13, size_hint_y=None, height=56,
                        text_size=(380, None), halign="left")
            self.match_result_box.add_widget(row)

    # ---- 组合日志 ----
    def _build_log_tab(self):
        self.log_list_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.log_list_box.bind(minimum_height=self.log_list_box.setter("height"))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(self.log_list_box)

        layout = BoxLayout(orientation="vertical", padding=12, spacing=10)
        self.log_search = text_input("搜索名称/备注")
        self.log_search.bind(text=self.on_log_search)
        layout.add_widget(self.log_search)
        layout.add_widget(sv)
        return layout

    def on_log_search(self, inst, val):
        self.refresh_logs(val.strip())

    def refresh_logs(self, term=""):
        if not hasattr(self, "log_list_box"):
            return
        self.log_list_box.clear_widgets()
        for r in store.fetch_logs(term):
            row = BoxLayout(orientation="vertical", size_hint_y=None, height=84,
                            padding=(6, 4), spacing=2)
            head = "{}　合计 {}　{}".format(r["name"], logic.fmt_money(r["total"]),
                                           r["created_at"])
            row.add_widget(Label(text=head, color=_rgb(C_TEXT), font_size=14,
                                 text_size=(360, None), halign="left", size_hint_y=None,
                                 height=26))
            row.add_widget(Label(text="备注：" + (r["remark"] or "（空）"),
                                 color=_rgb(C_MUTED), font_size=12,
                                 text_size=(360, None), halign="left", size_hint_y=None,
                                 height=22))
            btns = BoxLayout(orientation="horizontal", size_hint_y=None, height=30, spacing=6)
            btns.add_widget(make_btn("查看", lambda inst, rid=r["id"]: self.view_log(rid),
                                     bg=C_PRIMARY, width=80, height=30, font_size=13))
            btns.add_widget(make_btn("编辑", lambda inst, rid=r["id"]: self.edit_log(rid),
                                     bg=C_MUTED, width=80, height=30, font_size=13))
            btns.add_widget(make_btn("删", lambda inst, rid=r["id"]: self.del_log(rid),
                                     bg=C_ERROR, width=54, height=30, font_size=13))
            row.add_widget(btns)
            self.log_list_box.add_widget(row)

    def view_log(self, rid):
        raw = store.fetch_log_detail(rid)
        try:
            items = json.loads(raw) if raw else []
        except Exception:
            items = []
        lines = "\n".join("%s  %s  %s  %s" % (
            it.get("name", ""), it.get("spec", ""), it.get("unit", ""),
            logic.fmt_money(it.get("price", 0))) for it in items)
        msg_popup("清单明细", lines or "（无明细）")

    def edit_log(self, rid):
        rows = store.fetch_logs("")
        cur = next((r for r in rows if r["id"] == rid), None)
        if not cur:
            return
        box = BoxLayout(orientation="vertical", padding=16, spacing=12)
        name_in = text_input("名称", text=cur["name"])
        remark_in = text_input("备注", text=cur["remark"] or "")
        box.add_widget(name_in)
        box.add_widget(remark_in)

        def save(inst):
            store.update_log(rid, name=name_in.text.strip(), remark=remark_in.text.strip())
            popup.dismiss()
            self.refresh_logs(self.log_search.text.strip())
            msg_popup("成功", "已保存")

        row = BoxLayout(orientation="horizontal", spacing=12, size_hint_y=None, height=44)
        row.add_widget(make_btn("取消", lambda inst: popup.dismiss(), bg=C_MUTED, width=120))
        row.add_widget(make_btn("保存", save, width=120))
        box.add_widget(row)
        popup = Popup(title="编辑日志", content=box, size_hint=(0.9, 0.7))
        popup.open()

    def del_log(self, rid):
        confirm_popup("删除", "确定删除该日志？",
                      lambda: (store.delete_log(rid), self.refresh_logs(self.log_search.text.strip())))

    # ---- 组合小工具 ----
    def _build_tool_tab(self):
        self.tool_result_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.tool_result_box.bind(minimum_height=self.tool_result_box.setter("height"))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(self.tool_result_box)

        layout = BoxLayout(orientation="vertical", padding=12, spacing=10)
        self.t_name = text_input("姓名")
        self.t_max = text_input("每条金额上限")
        self.t_total = text_input("合计金额")
        self.t_count = text_input("生成条数（自动）")
        self.t_total.bind(text=self.on_total_change)
        self.t_max.bind(text=self.on_total_change)
        for w in (self.t_name, self.t_max, self.t_total, self.t_count):
            layout.add_widget(w)
        layout.add_widget(make_btn("生成", lambda inst: self.do_generate(),
                                   size_hint=(1, None), height=44))
        row = BoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=46)
        row.add_widget(make_btn("复制", lambda inst: self.do_copy(), bg=C_MUTED,
                                size_hint=(1, None), height=44))
        row.add_widget(make_btn("存日志", lambda inst: self.do_save_log(), bg=C_PRIMARY_D,
                                size_hint=(1, None), height=44))
        layout.add_widget(row)
        self.tool_result_box_parent = sv
        layout.add_widget(sv)
        return layout

    def on_total_change(self, inst, val):
        try:
            total = float(self.t_total.text or 0)
            maxv = float(self.t_max.text or 0)
            if total > 0 and maxv > 0:
                self.t_count.text = str(logic.calc_min_count(total, maxv))
        except ValueError:
            pass

    def do_generate(self):
        try:
            total = float(self.t_total.text or 0)
            maxv = float(self.t_max.text or 0)
        except ValueError:
            msg_popup("提示", "金额需为数字")
            return
        if total <= 0 or maxv <= 0:
            msg_popup("提示", "请填写合计金额与每条上限")
            return
        count = int(self.t_count.text) if self.t_count.text.strip() else None
        try:
            nums = logic.gen_random_combo(total, maxv, count)
        except ValueError as e:
            msg_popup("提示", str(e))
            return
        self._last_nums = nums
        self.tool_result_box.clear_widgets()
        for i, v in enumerate(nums, 1):
            self.tool_result_box.add_widget(Label(
                text="第 %d 条：%s" % (i, logic.fmt_money(v)), color=_rgb(C_TEXT),
                font_size=15, size_hint_y=None, height=38, text_size=(360, None),
                halign="left"))

    def do_copy(self):
        if not hasattr(self, "_last_nums"):
            msg_popup("提示", "请先生成")
            return
        text = logic.build_copy_text(self.t_name.text.strip(), self._last_nums,
                                     float(self.t_total.text or 0))
        Clipboard.copy(text)
        msg_popup("已复制", text)

    def do_save_log(self):
        if not hasattr(self, "_last_nums"):
            msg_popup("提示", "请先生成")
            return
        total = float(self.t_total.text or 0)
        detail = json.dumps(
            [{"name": self.t_name.text.strip() or "未命名", "price": v} for v in self._last_nums],
            ensure_ascii=False)
        store.insert_log(self.t_name.text.strip() or "未命名", total, detail, remark="")
        self.refresh_logs("")
        msg_popup("成功", "已保存到组合日志")


def Clock_schedule_once(func, t):
    """延迟调用封装（避免在类里反复 import Clock）。"""
    from kivy.clock import Clock
    Clock.schedule_once(func, t)


# ---------------- App ----------------
class BaibaoApp(App):
    def build(self):
        global CONFIG_DIR
        CONFIG_DIR = self.user_data_dir
        store.DB_PATH = os.path.join(CONFIG_DIR, "baibao.db")
        store.init_db()
        # 首次启动：若药品表为空，自动灌入桌面版已导入的种子数据
        seeded = store.seed_medicines_if_empty()
        if seeded:
            print("seeded %d medicines from desktop data" % seeded)
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        return sm


if __name__ == "__main__":
    BaibaoApp().run()
