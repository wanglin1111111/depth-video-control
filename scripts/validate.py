#!/usr/bin/env python3
"""validate.py — depth-video-control 镜头计划六维校验器

输入: 镜头计划 JSON（schema 见 tests/sample_good.json）
  {
    "shots": [
      {
        "id": "SHOT-1",
        "route": "depth" | "gacha",          # 路由：深度路线 / 抽卡路线
        "crash_points": [],                   # 预检命中的崩点，枚举见下
        "depth": {                           # route=depth 时必填
          "source_video": "a.mp4",
          "estimator": "depth-anything-v2",
          "acceptance": {                    # 四条验收，见 workflow.md
            "structure_ok": true,            # 结构正确
            "temporal_ok": true,             # 时序连续
            "crash_scan_ok": true,           # 崩点扫描通过
            "motion_ok": true                # 运动可辨
          }
        },
        "prompt": "红裙女人……",               # 提示词（三要素）
        "prompt_elements": {                 # 三要素声明，三项均须非空
          "subject": "红裙女人，湿发贴脸",
          "material": "写实电影质感，雨水反光皮肤与绸缎",
          "lighting": "雨夜霓虹，青橙对比"
        },
        "iteration": 0                       # 已迭代次数（同一镜头重生成计数）
      }
    ]
  }

六维校验（任一 FAIL → exit 1）：
  D1 路由合法：route ∈ {depth, gacha}，且每个 shot 都有 route
  D2 崩点纪律：crash_points 命中任一崩点时，route 不得为 depth（一票改路由）
  D3 深度验收：route=depth 时 depth 块完整且四条验收全 true
  D4 三要素封顶：prompt_elements 三项非空；且 prompt/各要素中不含禁写清单词
     （构图/站位/运镜/空间关系类——这些已由深度接管；gacha 路线豁免 D4b 禁写词）
  D5 迭代纪律：iteration >= 2 且不满意点类型未声明回实拍 → 要求 "reshoot" 标记
     （简化：iteration >= 2 时必须有 reshoot=true 或 status="accepted"）
  D6 唯一性：shot id 全局唯一

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import re
import sys

CRASH_POINTS = {"occlusion", "transparent", "reflective", "motion_blur"}
ROUTES = {"depth", "gacha"}

# 禁写清单（D4b）：构图/站位/运镜/空间关系类词。
# 注意：只拦"描述空间结构/镜头运动"的词，动作词（转身/挥手）与强度词（强烈晃动感）不在内。
FORBIDDEN = [
    # 构图/站位
    "前景", "背景", "构图", "遮挡", "站在一起", "谁在前", "谁在后",
    "画面左", "画面右", "特写", "远景", "全景景别",
    # 运镜
    "横移", "推镜头", "拉镜头", "摇镜头", "移镜头", "跟拍", "手持",
    "镜头运动", "镜头从左", "镜头从右", "camera movement", "pan",
    "dolly", "tracking shot",
    # 空间关系
    "透视", "三米处", "距离感",
]

FORBIDDEN_RE = re.compile(
    "|".join(re.escape(w) for w in FORBIDDEN),
    re.IGNORECASE,
)


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def validate(plan):
    checks = []
    shots = plan.get("shots")
    if not isinstance(shots, list) or not shots:
        fail(checks, "D0", "shots 必须是非空数组")
        return checks

    seen_ids = set()
    for i, s in enumerate(shots):
        where = f"shots[{i}]"
        sid = s.get("id")
        if sid:
            where = f"shots[{i}]({sid})"

        # D6 唯一性
        if sid in seen_ids:
            fail(checks, "D6", f"{where}: id 重复: {sid}")
        seen_ids.add(sid)

        # D1 路由合法
        route = s.get("route")
        if route not in ROUTES:
            fail(checks, "D1", f"{where}: route 缺失或非法: {route!r}（须为 depth/gacha）")
            continue
        ok(checks, "D1", f"{where}: route={route}")

        # D2 崩点纪律
        cps = set(s.get("crash_points") or [])
        unknown = cps - CRASH_POINTS
        if unknown:
            fail(checks, "D2", f"{where}: 未知崩点枚举: {sorted(unknown)}")
        if route == "depth" and cps:
            fail(checks, "D2", f"{where}: 命中崩点 {sorted(cps)} 仍走 depth 路线——一票改路由")
        else:
            ok(checks, "D2", f"{where}: 崩点纪律通过（命中 {sorted(cps) or '无'}）")

        # D3 深度验收
        if route == "depth":
            depth = s.get("depth") or {}
            if not depth.get("source_video"):
                fail(checks, "D3", f"{where}: depth.source_video 缺失")
            if not depth.get("estimator"):
                fail(checks, "D3", f"{where}: depth.estimator 缺失")
            acc = depth.get("acceptance") or {}
            for k in ("structure_ok", "temporal_ok", "crash_scan_ok", "motion_ok"):
                if acc.get(k) is not True:
                    fail(checks, "D3", f"{where}: 深度验收未过: {k}")
            if all(acc.get(k) is True for k in ("structure_ok", "temporal_ok", "crash_scan_ok", "motion_ok")):
                ok(checks, "D3", f"{where}: 深度序列四条验收全过")
        else:
            ok(checks, "D3", f"{where}: 非深度路线，深度验收豁免")

        # D4 三要素封顶
        pe = s.get("prompt_elements") or {}
        for k in ("subject", "material", "lighting"):
            if not (pe.get(k) or "").strip():
                fail(checks, "D4", f"{where}: 三要素缺失: {k}")
        if all((pe.get(k) or "").strip() for k in ("subject", "material", "lighting")):
            ok(checks, "D4", f"{where}: 三要素齐全")
        # D4b 禁写词（仅 depth 路线；gacha 路线构图只能靠文字，豁免）
        if route == "depth":
            text = "\n".join(
                [s.get("prompt") or "", pe.get("subject") or "", pe.get("material") or "", pe.get("lighting") or ""]
            )
            hits = sorted(set(m.group(0) for m in FORBIDDEN_RE.finditer(text)))
            if hits:
                fail(checks, "D4", f"{where}: depth 路线提示词混入禁写词: {hits}（构图/运镜已由深度接管）")
            else:
                ok(checks, "D4", f"{where}: 提示词无禁写词")

        # D5 迭代纪律
        it = s.get("iteration", 0)
        if not isinstance(it, int) or it < 0:
            fail(checks, "D5", f"{where}: iteration 非法: {it!r}")
        elif it >= 2 and not s.get("reshoot") and s.get("status") != "accepted":
            fail(checks, "D5", f"{where}: 迭代 {it} 次仍不满意——须声明 reshoot=true 或 status=accepted（停止在语言层打转）")
        else:
            ok(checks, "D5", f"{where}: 迭代纪律通过（iteration={it}）")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py shotplan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
