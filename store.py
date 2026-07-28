"""百宝箱 · 存储层（SQLite）。

桌面版路径在 exe 同级 Data/；Android 版路径在 Kivy app.user_data_dir。
本模块不依赖 kivy：DB_PATH 由调用方在运行时赋值（main.py 里设置），
便于在不启动 GUI 的情况下做 headless 测试（测试时指向临时文件）。
"""

import os
import json
import sqlite3

# 默认路径（仅兜底；main.py 在 Android 上会覆盖为 app.user_data_dir）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baibao.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            spec TEXT,
            unit TEXT,
            price REAL,
            count INTEGER,
            subtotal REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS combo_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            total REAL,
            created_at TEXT,
            remark TEXT,
            detail TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------------- 药品清单 ----------------

def insert_medicine(name, spec, unit, price, count):
    price = float(price or 0)
    count = int(count or 0)
    subtotal = price * count
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO medicines (name, spec, unit, price, count, subtotal) VALUES (?,?,?,?,?,?)",
        (name, spec, unit, price, count, subtotal))
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def fetch_medicines(term=""):
    conn = _conn()
    cur = conn.cursor()
    if term:
        like = "%" + term + "%"
        cur.execute("SELECT * FROM medicines WHERE name LIKE ? OR spec LIKE ? ORDER BY id",
                    (like, like))
    else:
        cur.execute("SELECT * FROM medicines ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def delete_medicine(mid):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE id=?", (mid,))
    conn.commit()
    conn.close()


def clear_medicines():
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines")
    conn.commit()
    conn.close()


def seed_medicines_if_empty():
    """首次启动时，若药品表为空且存在 seed_medicines.json，则自动灌入。

    种子文件位于本模块同目录，由桌面版已导入的药品清单导出而来。
    只在「表为空」时写入，避免重复灌入或覆盖用户数据。
    """
    if count_medicines() > 0:
        return 0
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "seed_medicines.json")
    if not os.path.exists(seed_path):
        return 0
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        return 0
    n = 0
    for r in rows:
        try:
            price = float(r.get("price", 0) or 0)
            cnt = int(r.get("count", 1) or 1)
        except (TypeError, ValueError):
            price, cnt = 0, 1
        insert_medicine(r.get("name", ""), r.get("spec", ""), r.get("unit", ""),
                        price, cnt)
        n += 1
    return n


def count_medicines():
    conn = _conn()
    cur = conn.cursor()
    c = cur.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]
    conn.close()
    return c


# ---------------- 组合日志 ----------------

def insert_log(name, total, detail, remark=""):
    from datetime import datetime
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO combo_logs (name, total, created_at, remark, detail) VALUES (?,?,?,?,?)",
        (name, float(total or 0), created_at, remark, detail))
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def fetch_logs(term=""):
    conn = _conn()
    cur = conn.cursor()
    if term:
        like = "%" + term + "%"
        cur.execute("SELECT * FROM combo_logs WHERE name LIKE ? OR remark LIKE ? ORDER BY id DESC",
                    (like, like))
    else:
        cur.execute("SELECT * FROM combo_logs ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def fetch_log_detail(log_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT detail FROM combo_logs WHERE id=?", (log_id,))
    row = cur.fetchone()
    conn.close()
    return row["detail"] if row else ""


def update_log(log_id, name=None, remark=None):
    conn = _conn()
    cur = conn.cursor()
    if name is not None:
        cur.execute("UPDATE combo_logs SET name=? WHERE id=?", (name, log_id))
    if remark is not None:
        cur.execute("UPDATE combo_logs SET remark=? WHERE id=?", (remark, log_id))
    conn.commit()
    conn.close()


def delete_log(log_id):
    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM combo_logs WHERE id=?", (log_id,))
    conn.commit()
    conn.close()
