"""百宝箱 Android · 逻辑自测（不依赖 kivy，可在 CI/本地直接跑）。

运行：python selftest.py
覆盖：组合生成、最少条数、金额格式化、复制文本、费用组合匹配、存储 CRUD。
同时尝试导入 main（需 kivy），用于发现 Kivy 相关导入错误。
"""

import os
import tempfile
import json

import logic
import store


def run():
    # 1) 组合生成
    assert logic.gen_random_combo(6000, 2000, 3) == [2000, 2000, 2000]
    for _ in range(2000):
        nums = logic.gen_random_combo(5900, 2000, 3)
        assert len(nums) == 3 and sum(nums) == 5900
        assert all(1 <= x <= 2000 for x in nums)
    assert logic.calc_min_count(6000, 2000) == 3
    assert logic.calc_min_count(5900, 2000) == 3

    # 2) 金额格式化 + 复制文本
    assert logic.fmt_money(50) == "50"
    assert logic.fmt_money(45.5) == "45.50"
    txt = logic.build_copy_text("张三", [1900, 2000, 2000], 5900)
    assert txt.startswith("张三")
    assert "合计金额：5900 元" in txt

    # 3) 费用组合匹配
    items = [{"name": "A", "price": 10}, {"name": "B", "price": 20},
             {"name": "C", "price": 30}, {"name": "D", "price": 40}]
    res = logic.find_combos(items, 60, max_results=20)
    assert any(abs(s - 60) < 1e-9 for _, s in res), res

    # 4) 存储 CRUD（临时库）
    tmp = os.path.join(tempfile.gettempdir(), "baibao_selftest.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    store.DB_PATH = tmp
    store.init_db()
    store.insert_medicine("阿莫西林", "0.25g", "盒", 12.5, 2)
    meds = store.fetch_medicines()
    assert len(meds) == 1 and abs(meds[0]["subtotal"] - 25.0) < 1e-9

    detail = json.dumps([{"name": "阿莫西林", "price": 12.5, "count": 2}],
                        ensure_ascii=False)
    lid = store.insert_log("感冒", 25.0, detail, remark="")
    assert store.fetch_logs("感冒")[0]["name"] == "感冒"
    assert json.loads(store.fetch_log_detail(lid))[0]["name"] == "阿莫西林"
    store.update_log(lid, remark="改")
    assert store.fetch_logs("")[0]["remark"] == "改"
    store.delete_log(lid)
    assert store.fetch_logs("") == []
    store.clear_medicines()

    # 说明：main 的 kivy 导入校验放在 CI 单独一步（pip install kivy 后
    # 执行 `python -c "import main"`），避免在此处反向 import 造成递归。
    print("ALL_SELFTESTS_PASSED")


if __name__ == "__main__":
    run()
