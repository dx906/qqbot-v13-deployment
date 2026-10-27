# -*- coding: utf-8 -*-
"""遗留项 3 验收：V1.1 真实启动后，L3 档案层 / L2 行为层 / 插件 patch / 第4路召回
在**运行时**是否真的加载了（不看代码、不看配置，只看真实日志与真实接口）。

做法：
  1. 起一个真实 webchat 会话并发一条真实消息（触发懒加载）
  2. 抓 AstrBot 日志里 4 条关键运行时证据
  3. 直接打 1936 / 8127 / 6381 三个接口，证明服务活着
输出同时写到 v11-evidence/runtime-verification.txt
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

V11 = Path(r"D:\AI\QQBot-v13")
LOG = V11 / "logs" / "astrbot-v11.log"
EVID = V11 / "v11-evidence"

DASH = "http://127.0.0.1:6381"
OV = "http://127.0.0.1:1936"
SVC = "http://127.0.0.1:8127"
USER = "astrbot"

lines: list[str] = []


def say(s: str = "") -> None:
    print(s)
    lines.append(s)


def http(method: str, url: str, payload: dict | None = None,
         token: str | None = None, timeout: int = 90) -> tuple[int, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def find_password() -> str | None:
    """从启动日志抓 --reset-password 生成的初始密码，或读已保存的密码文件。

    AstrBot 只会在 `--reset-password` 那一次打印 `Initial password:`；
    之后的普通启动不再打印。所以这里先查日志，再查 V1.1 私有密码文件
    `ov-v13/dashboard-pw.txt`（由 _setup/reset-pw-v11.cmd 写入）。
    """
    if LOG.exists():
        txt = LOG.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(r"Initial password:\s*(\S+)", txt)
        if hits:
            return hits[-1]
    pwfile = V11 / "ov-v13" / "dashboard-pw.txt"
    if pwfile.exists():
        pw = pwfile.read_text(encoding="utf-8-sig").strip()
        if pw:
            return pw
    return None


def login() -> str | None:
    """尝试登录；密码未知时用 --reset-password 重置一次。"""
    for pw in ([find_password()] if find_password() else []) + ["astrbot"]:
        if not pw:
            continue
        c, b = http("POST", f"{DASH}/api/auth/login",
                    {"username": USER, "password": pw}, timeout=20)
        if c == 200:
            try:
                return json.loads(b)["data"]["token"]
            except Exception:
                pass
    return None


def trigger_real_message(token: str) -> tuple[int, str]:
    """发一条真实消息，触发 resident/behavior/persona 三段懒加载。"""
    sid = f"v11-runtime-verify-{int(time.time())}"
    return http("POST", f"{DASH}/api/chat/send",
                {"message": "你好，今天有点累，想听点音乐", "session_id": sid},
                token=token, timeout=150)


def grep(pattern: str) -> list[str]:
    if not LOG.exists():
        return []
    out = []
    for ln in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.search(pattern, ln):
            out.append(re.sub(r"\x1b\[[0-9;]*m", "", ln).strip())
    return out


def main() -> int:
    say("=" * 80)
    say("遗留项 3：V1.1 重启后运行时加载验证")
    say(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    say("=" * 80)

    # ---------- 1) 三个服务真实存活 ----------
    say()
    say("【1】服务端口真实存活（HTTP 实测，非端口猜测）")
    for name, url in (("AstrBot Dashboard", f"{DASH}/"),
                      ("V1.1 OpenViking", f"{OV}/health"),
                      ("persona-svc 召回", f"{SVC}/health")):
        c, b = http("GET", url, timeout=30)
        summary = b.strip().replace("\n", " ")[:150]
        say(f"  HTTP {c}  {name:22s} {url}")
        say(f"        {summary}")
    say()

    # ---------- 2) 触发真实消息 ----------
    say("【2】触发真实消息（懒加载只会在真实请求路径上发生）")
    token = login()
    if not token:
        say("  [WARN] 未能登录 dashboard，跳过发消息；改用日志交叉验证")
    else:
        c, body = trigger_real_message(token)
        ev = re.findall(r'"type":\s*"(\w+)"', body or "")
        say(f"  POST /api/chat/send -> HTTP {c}")
        say(f"  事件序列: {ev[:8]}")
        say(f"  响应片段: {body[:220].replace(chr(10), ' ')}")
    say()

    # ---------- 3) 四条运行时证据 ----------
    say("【3】运行时日志证据（原始行，来自真实启动的 astrbot-v11.log）")
    checks = [
        ("L3 常驻画像块 resident_profile",
         r"\[OV\] resident profile loaded"),
        ("L2 行为层 behavior",
         r"\[OV\] behavior rules loaded"),
        ("第 4 路 persona 动态召回真实注入",
         r"\[OV\] persona recall injected"),
        ("插件 patch: humanlike 真实加载",
         r"\[humanlike\] 已加载"),
        ("插件 hook on_astrbot_loaded",
         r"hook\(on_astrbot_loaded\) -> astrbot_plugin_openviking_memory"),
        ("OV 指向 1936（隔离确认）",
         r"\[OV\] server reachable at http://127\.0\.0\.1:1936"),
        ("第 4 路无超时/失败",
         r"persona recall (timed out|failed)"),
    ]
    ok_count = 0
    for label, pat in checks:
        hits = grep(pat)
        if label.endswith("无超时/失败"):
            # 这类是「失败」模式：没有命中才算好
            ok = not hits
            say(f"  [{'PASS' if ok else 'WARN'}] {label} —— 命中 {len(hits)} 行（0 才好）")
            if hits:
                for h in hits[-2:]:
                    say(f"          {h[:160]}")
        else:
            ok = bool(hits)
            ok_count += ok
            say(f"  [{'PASS' if ok else 'FAIL'}] {label} —— 命中 {len(hits)} 行")
            if hits:
                say(f"          {hits[-1][:200]}")
    say()

    # ---------- 4) 服务自身元数据交叉证明 ----------
    say("【4】服务元数据（证明 V1.1 用的是自己的库 / 自己的嵌入）")
    c, b = http("GET", f"{SVC}/health", timeout=30)
    try:
        d = json.loads(b)
        say(f"  persona-svc db    = {d.get('db')}")
        say(f"  persona-svc count = {d.get('count')}  tiers={d.get('tiers')}")
        say(f"  persona-svc embed = {d.get('embed')}")
        isolated = str(d.get("db", "")).startswith(str(V11))
        real_embed = "openai:" in str(d.get("embed", ""))
        say(f"  [{'PASS' if isolated else 'FAIL'}] 库在 V1.1 内")
        say(f"  [{'PASS' if real_embed else 'FAIL'}] 真语义嵌入（非 hash）")
    except Exception as e:
        say(f"  [FAIL] 解析 /health 失败: {e}")
    say()

    # ---------- 5) 结论 ----------
    say("=" * 80)
    total_checks = len([c for c in checks if not c[0].endswith("无超时/失败")])
    say(f"运行时日志证据通过 {ok_count}/{total_checks} 项")
    say("=" * 80)

    EVID.mkdir(parents=True, exist_ok=True)
    out = EVID / "runtime-verification.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n证据 -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
