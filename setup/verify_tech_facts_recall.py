# -*- coding: utf-8 -*-
"""遗留项 1 验收：59 条技术类事实在 V1.1 的 OV（1936）里能否被真实召回。

判定口径（三档，全部记录）：
  top1    —— 首条就是期望文件（最严）
  top3    —— 期望文件出现在前 3（生产实际用这个：recall_limit=3）
  anywhere—— 出现在返回集里（limit=10）
另外记录「是否在库中」（glob），把「没入库」和「入了库但排不上」区分开。
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:1936"
KEY = "ZGVmYXVsdA.Ym90.MDQwNjBkZWJmMWIxMjQ2Mjg5Yjc4MTY4NWNjNjU3OGQ2NjU3NzI4ODE5MDkzM2M2MmU5ZWVjZGM5NTAwNDNiNw"
MANIFEST = Path(r"D:\AI\persona-base\ov_ingest_manifest.json")
OUT = Path(r"D:\AI\QQBot-v13\v11-evidence\tech-facts-recall.json")
PREF_URI = "viking://user/bot/memories/preferences"


def post(path: str, payload: dict, timeout: int = 200):
    h = {"Authorization": f"Bearer {KEY}", "X-API-Key": KEY,
         "X-OpenViking-Account": "default", "X-OpenViking-User": "bot",
         "Content-Type": "application/json"}
    r = urllib.request.Request(BASE + path,
                               data=json.dumps(payload, ensure_ascii=False).encode(),
                               headers=h, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace"))


def mems(res: dict) -> list[dict]:
    """find 的结果里记忆在 'memories' 键（不是 resources）。"""
    return (res or {}).get("memories") or []


def glob_exists(name: str) -> bool:
    c, j = post("/api/v1/search/glob",
                {"pattern": f"**/{name}", "uri": "viking://user/bot", "node_limit": 5})
    return c == 200 and bool(((j.get("result") or {}).get("matches")))


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    techs: list[str] = man["tech_files"]
    print(f"manifest: life={man['life']} tech={man['tech']} inserted={man['inserted']}")
    print(f"tech_files = {len(techs)} 条")
    print(f"target = {BASE}  {PREF_URI}")
    print("=" * 78)

    tests = []
    n_top1 = n_top3 = n_any = n_inlib = 0
    for i, name in enumerate(techs, 1):
        q = name[:-3] if name.endswith(".md") else name
        exists = glob_exists(name)
        c, j = post("/api/v1/search/find", {
            "query": q, "target_uri": [PREF_URI],
            "limit": 10, "score_threshold": 0.0})
        items = mems(j.get("result") or {}) if c == 200 else []
        uris = [it.get("uri", "") for it in items]
        scores = [it.get("score") for it in items]
        ranks = [k + 1 for k, u in enumerate(uris) if u.endswith("/" + name)]
        rank = ranks[0] if ranks else None
        n_top1 += (rank == 1)
        n_top3 += (rank is not None and rank <= 3)
        n_any += (rank is not None)
        n_inlib += exists
        tests.append({"n": i, "query": q, "expected": name, "in_library": exists,
                      "rank": rank, "returned": len(items),
                      "top_uri": uris[0] if uris else "",
                      "top_score": scores[0] if scores else None,
                      "uris": uris})
        flag = "OK " if rank == 1 else ("~  " if (rank or 99) <= 3 else
                                       ("IN " if rank else ("LIB" if exists else "MISS")))
        print(f"[{i:2}/59] {flag} rank={rank}  {name}")

    total = len(techs)
    print("=" * 78)
    print(f"在库中（glob 可见）      : {n_inlib}/{total}  = {n_inlib/total*100:.1f}%")
    print(f"召回 top1 命中           : {n_top1}/{total}  = {n_top1/total*100:.1f}%")
    print(f"召回 top3 命中           : {n_top3}/{total}  = {n_top3/total*100:.1f}%")
    print(f"召回 limit=10 内命中     : {n_any}/{total}  = {n_any/total*100:.1f}%")

    miss = [t for t in tests if t["rank"] is None]
    if miss:
        print(f"\n未进前 10 的 {len(miss)} 条：")
        for t in miss:
            print(f"  in_library={t['in_library']}  {t['expected']}  -> top={t['top_uri'].split('/')[-1]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ov": BASE, "workspace": r"D:\AI\QQBot-v13\ov-data",
        "target_uri": PREF_URI, "manifest": man,
        "summary": {"total": total, "in_library": n_inlib,
                    "top1": n_top1, "top3": n_top3, "within10": n_any},
        "tests": tests,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n证据 -> {OUT}")
    return 0 if n_any == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
