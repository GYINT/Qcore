# -*- coding: utf-8 -*-
"""QCM 独立 AI 搜索引擎直连（V8.4 · Infoseek 不可用兜底）

用途：Infoseek 未安装/不可用时，QCM 直接调用 AI 搜索 API 获取真实联网锚点。
零重复建设注记：Infoseek 可用时优先复用其 search_web（5 引擎成熟链）；
本模块仅作**独立兜底**（不依赖 Infoseek 代码 · urllib 无第三方依赖）。

引擎降级链：
  1. 智谱 GLM web_search（ZHIPU_API_KEY · 公测免费 · 聚合搜狗/夸克）
  2. 博查 Bocha（BOCHA_API_KEY · 0.02 元/次）
  3. 无任何 Key → 返回 []（调用方降级 LLM 语义消解 / 规则）

输出统一：[{"url", "title", "snippet"}, ...]（url 去重 · 失败 [] 不伪造）
"""
import json
import os
import urllib.request
from typing import List, Dict


def _glm_web_search(query: str, max_results: int = 5) -> List[Dict]:
    """智谱 GLM web_search（公测免费 · 聚合智谱自研 + 搜狗 + 夸克）"""
    key = os.environ.get("ZHIPU_API_KEY", "")
    if not key:
        return []
    payload = json.dumps({"search_query": query, "search_engine": "search_pro",
                          "count": max_results, "search_intent": False}).encode("utf-8")
    req = urllib.request.Request(
        "https://open.bigmodel.cn/api/paas/v4/web_search", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    out = []
    for r in (data.get("search_result") or []):
        u = r.get("link")
        if u and u not in [x["url"] for x in out]:
            out.append({"url": u, "title": r.get("title") or query,
                        "snippet": (r.get("content") or "")[:200]})
        if len(out) >= max_results:
            break
    return out


def _bocha_search(query: str, max_results: int = 5) -> List[Dict]:
    """博查 Bocha 搜索（国内独立搜索 API · 0.02 元/次）"""
    key = os.environ.get("BOCHA_API_KEY", "")
    if not key:
        return []
    payload = json.dumps({"query": query, "count": max_results,
                          "freshness": "noLimit"}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.bochaai.com/v1/web-search", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    out = []
    for r in ((data.get("data") or {}).get("webPages", {}).get("value", [])):
        u = r.get("url")
        if u and u not in [x["url"] for x in out]:
            out.append({"url": u, "title": r.get("name") or query,
                        "snippet": (r.get("snippet") or "")[:200]})
        if len(out) >= max_results:
            break
    return out


def ai_search(query: str, max_results: int = 5) -> List[Dict]:
    """AI 搜索直连（多引擎降级 · 统一输出）· 无 Key → []"""
    engines = [
        ("智谱", _glm_web_search),
        ("博查", _bocha_search),
    ]
    for name, fn in engines:
        try:
            hits = fn(query, max_results)
            if hits:
                return hits
        except Exception:
            continue  # 单引擎失败 → 降级下一引擎
    return []


def main():
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "SPC 统计过程控制 方法"
    hits = ai_search(q, max_results=5)
    print(f"AI 搜索「{q}」: {len(hits)} 条")
    for h in hits[:5]:
        print(f"  [{h['title'][:30]}] {h['url'][:60]}")
        print(f"    {h['snippet'][:60]}")
    if not hits:
        print("  （无结果 · 请配置 ZHIPU_API_KEY 或 BOCHA_API_KEY）")


if __name__ == "__main__":
    main()
