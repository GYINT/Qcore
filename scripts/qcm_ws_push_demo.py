#!/usr/bin/env python3
"""qcm_ws_push_demo.py — QCM MCP WS 旁路订阅演示客户端

用法（先启动主服务，默认旁路端口 8765）：
  # 终端 1：启动 stdio 或 http 主服务（自动带 WS 旁路）
  python qcm_mcp_server.py --transport http --port 8080
  # 终端 2：订阅工具调用事件
  python qcm_ws_push_demo.py [--port 8765] [--token <bearer>]

订阅到的事件格式（graphql-ws next）：
  {"tool": "qcm_solve_problem", "arguments": {...}, "time": "2026-08-13T00:00:00"}
"""
import argparse
import asyncio
import json
import sys

import websockets


async def main(port: int, token: str = ""):
    uri = f"ws://127.0.0.1:{port}"
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with websockets.connect(uri, additional_headers=headers) as ws:
        # 1. connection_init → connection_ack
        await ws.send(json.dumps({"type": "connection_init"}))
        ack = json.loads(await ws.recv())
        assert ack["type"] == "connection_ack", ack
        print(f"[demo] 已连接 {uri} · 订阅 toolCalled 事件（Ctrl+C 退出）", flush=True)

        # 2. subscribe toolCalled
        await ws.send(json.dumps({
            "type": "subscribe", "id": "demo",
            "payload": {"query": "subscription { toolCalled { tool arguments time } }"},
        }))

        # 3. 持续接收 next 事件
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "next":
                ev = msg["payload"]["data"]["toolCalled"]
                print(f"[demo] toolCalled: {ev['tool']} @ {ev['time']}"
                      f"  args={json.dumps(ev.get('arguments'), ensure_ascii=False)[:120]}",
                      flush=True)
            elif msg.get("type") == "complete":
                print("[demo] 订阅完成", flush=True)
                break
            elif msg.get("type") == "error":
                print(f"[demo] 订阅错误: {msg.get('payload')}", flush=True)
                break


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="QCM WS 旁路订阅演示")
    ap.add_argument("--port", type=int, default=8765, help="旁路端口（默认 8765）")
    ap.add_argument("--token", default="", help="Bearer token（主服务 --require-token 时需要）")
    args = ap.parse_args()
    try:
        asyncio.run(main(args.port, args.token))
    except ConnectionRefusedError:
        print(f"[demo] 无法连接 ws://127.0.0.1:{args.port} —— 请先启动主服务：", flush=True)
        print(f"       python qcm_mcp_server.py --transport http --port 8080"
              f" --ws-push-port {args.port}", flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[demo] 退出", flush=True)
