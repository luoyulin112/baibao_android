"""百宝箱 · 纯逻辑层（桌面版与 Android 版共用思路，可独立测试）。

包含：
  - gen_random_combo : 随机生成若干条金额，每条 <= 上限、合计恰等于目标
  - calc_min_count   : 按 合计/上限 计算最少条数（向上取整）
  - fmt_money        : 金额格式化（整数不带小数，否则两位）
  - build_copy_text  : 拼接「组合小工具」复制文本
  - find_combos      : 费用组合匹配（从药品列表中找合计接近目标的组合，有界搜索）
"""

import random


def fmt_money(v):
    """金额格式化：整数不带小数（50 -> '50'），否则保留两位（45.5 -> '45.50'）。"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = 0.0
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return "%.2f" % v


def calc_min_count(total, maxv):
    """最少条数 = ceil(total / maxv)，至少 1 条。"""
    total = max(0, int(round(float(total))))
    maxv = max(1, int(round(float(maxv))))
    if total <= 0:
        return 1
    return (total + maxv - 1) // maxv


def gen_random_combo(total, maxv, count=None):
    """随机生成 count 条正整数，每条落在区间 [1, maxv]，且合计恰等于 total。

    约束：count*maxv >= total >= count（否则无解，抛出 ValueError）。
    若未传 count，则自动按 calc_min_count(total, maxv) 计算最少条数。
    """
    total = int(round(float(total)))
    maxv = int(round(float(maxv)))
    if maxv < 1:
        raise ValueError("每条金额上限必须 >= 1")
    if count is None:
        count = calc_min_count(total, maxv)
    count = max(1, int(count))
    if total < count:
        raise ValueError("合计金额 %.2f 小于最少条数 %d（每条至少 1）" % (total, count))
    if total > count * maxv:
        raise ValueError("合计金额 %.2f 超过 上限%d × 条数%d，请增大条数或上限" % (total, maxv, count))

    # 先每条放 1，剩余待分配
    nums = [1] * count
    remain = total - count
    cap = maxv - 1  # 每条还能加多少
    # 随机把 remain 分配到各条，保证每条不超 maxv
    guard = count * 200 + 1000
    while remain > 0 and guard > 0:
        guard -= 1
        i = random.randrange(count)
        room = cap - (nums[i] - 1)
        if room <= 0:
            continue
        take = random.randint(1, min(room, remain))
        nums[i] += take
        remain -= take
    if remain != 0:
        # 理论上不会走到这里（约束保证可解），兜底均匀补齐
        while remain > 0:
            for i in range(count):
                if remain <= 0:
                    break
                room = cap - (nums[i] - 1)
                if room > 0:
                    take = min(room, remain)
                    nums[i] += take
                    remain -= take
    random.shuffle(nums)
    return nums


def build_copy_text(name, nums, total):
    """组合小工具复制文本：名字 + 各条金额 + 合计金额。"""
    lines = []
    if name:
        lines.append("%s" % name)
    for v in nums:
        lines.append(fmt_money(v))
    lines.append("合计金额：%s 元" % fmt_money(total))
    return "\n".join(lines)


def find_combos(items, target, max_results=50, tol=0):
    """费用组合匹配：从 items（每项含 price）中找子集，使其合计尽量接近 target。

    items: list of dict，需含 'price'（数值）。
    返回：list of (subset_list, subtotal)，按 |subtotal-target| 升序，最多 max_results 组。
    采用有界 DFS：超过 target 即剪枝，限制结果数量与搜索深度，避免爆炸。
    """
    try:
        target = float(target)
    except (TypeError, ValueError):
        target = 0.0
    if target <= 0:
        return []

    prices = []
    for it in items:
        try:
            p = float(it.get("price", 0) or 0)
        except (TypeError, ValueError):
            p = 0.0
        if p > 0:
            prices.append((p, it))
    prices.sort(key=lambda x: x[0], reverse=True)

    results = []

    def dfs(start, chosen, subtotal):
        if len(results) >= max_results:
            return
        diff = target - subtotal
        if abs(diff) <= tol:
            results.append((list(chosen), subtotal))
            return
        if subtotal > target:
            return  # 超出，剪枝
        for i in range(start, len(prices)):
            p, it = prices[i]
            if subtotal + p > target + tol:
                continue
            chosen.append(it)
            dfs(i + 1, chosen, subtotal + p)
            chosen.pop()
            if len(results) >= max_results:
                return

    dfs(0, [], 0.0)
    # 按接近程度排序
    results.sort(key=lambda r: abs(r[1] - target))
    return results[:max_results]


if __name__ == "__main__":
    # 简单自测（直接运行 python logic.py）
    assert gen_random_combo(6000, 2000, 3) == [2000, 2000, 2000]
    for _ in range(500):
        nums = gen_random_combo(5900, 2000, 3)
        assert len(nums) == 3 and sum(nums) == 5900 and all(1 <= x <= 2000 for x in nums)
    assert calc_min_count(6000, 2000) == 3
    assert calc_min_count(5900, 2000) == 3
    print("logic self-test OK")
