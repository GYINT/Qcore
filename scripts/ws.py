#!/usr/bin/env python3
"""qcm_ws.py — QCM MCP GraphQL Subscription over WebSocket

graphql-ws 协议（完整）：
  Client → Server: connection_init / subscribe / ping
  Server → Client: connection_ack / next / error / complete / pong

用法（server 侧）：
  from ws import run_graphql_ws_server
  run_graphql_ws_server(schema, port=8765, require_token=False, fixed_token=None)

协议流程：
  1. client 发 connection_init → server 回 connection_ack
  2. client 发 subscribe {id, payload: {query}} → server 持续发 next
  3. 完成 → server 发 complete
"""
import json
import asyncio
from typing import Any, Dict, Optional

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from graphql import parse, subscribe, validate


def _parse_payload(payload: Dict) -> Dict:
    """执行 GraphQL 查询/订阅"""
    query = payload.get("query", "")
    variables = payload.get("variables") or {}
    operation_name = payload.get("operationName")
    try:
        doc = parse(query)
    except Exception as e:
        return {"errors": [{"message": f"Parse error: {e}"}]}

    # 判断是否 subscription（OperationType 枚举比较 · 修复）
    from graphql import OperationType
    is_subscription = False
    for op in doc.definitions:
        if getattr(op, "operation", None) == OperationType.SUBSCRIPTION:
            is_subscription = True
            break

    if is_subscription:
        return {"type": "subscription", "doc": doc, "variables": variables}
    return {"type": "query", "doc": doc, "variables": variables}


async def _handle_ws(websocket, schema, require_token: bool, fixed_token: Optional[str],
                     jsonrpc_handler: Optional[Any] = None):
    """WebSocket 双协议处理

    - graphql-ws 协议：connection_init / subscribe / ping（GraphQL subscription）
    - JSON-RPC 协议：jsonrpc: 2.0 消息（MCP 兼容）
    """
    import secrets

    # 认证（可选）
    if require_token:
        try:
            headers = websocket.request.headers
            auth = headers.get("Authorization", "") if headers else ""
        except Exception:
            auth = ""
        if not (auth.startswith("Bearer ") and fixed_token
                and secrets.compare_digest(auth[7:], fixed_token)):
            await websocket.send(json.dumps({"type": "connection_error",
                                             "payload": {"message": "Unauthorized"}}))
            return

    # 活跃订阅任务
    subscriptions: Dict[str, asyncio.Task] = {}

    async for raw in websocket:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        msg_type = msg.get("type", "")
        msg_id = msg.get("id")

        # JSON-RPC 分流（MCP 协议兼容）
        if msg.get("jsonrpc") == "2.0" and jsonrpc_handler:
            try:
                response = jsonrpc_handler(msg)
                if response is not None:
                    await websocket.send(json.dumps(response, ensure_ascii=False))
            except Exception as e:
                await websocket.send(json.dumps({
                    "jsonrpc": "2.0", "id": msg.get("id"),
                    "error": {"code": -32603, "message": str(e)},
                }))
            continue

        if msg_type == "connection_init":
            await websocket.send(json.dumps({"type": "connection_ack"}))

        elif msg_type == "ping":
            await websocket.send(json.dumps({"type": "pong"}))

        elif msg_type == "subscribe":
            if not msg_id:
                continue
            parsed = _parse_payload(msg.get("payload", {}))

            if "errors" in parsed:
                await websocket.send(json.dumps({
                    "type": "error", "id": msg_id,
                    "payload": parsed["errors"],
                }))
                continue

            if parsed["type"] == "query":
                # 普通查询（graphql-ws 也支持）
                from graphql import execute_sync
                try:
                    v_errors = validate(schema, parsed["doc"])
                    if v_errors:
                        await websocket.send(json.dumps({
                            "type": "error", "id": msg_id,
                            "payload": [{"message": str(e)} for e in v_errors],
                        }))
                        continue
                    result = execute_sync(schema, parsed["doc"],
                                          variable_values=parsed["variables"])
                    if result.errors:
                        await websocket.send(json.dumps({
                            "type": "error", "id": msg_id,
                            "payload": [{"message": str(e)} for e in result.errors],
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "next", "id": msg_id,
                            "payload": {"data": result.data},
                        }))
                        await websocket.send(json.dumps({"type": "complete", "id": msg_id}))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "type": "error", "id": msg_id,
                        "payload": [{"message": str(e)}],
                    }))

            else:  # subscription
                async def _run_subscription(doc, variables, sid):
                    try:
                        v_errors = validate(schema, doc)
                        if v_errors:
                            await websocket.send(json.dumps({
                                "type": "error", "id": sid,
                                "payload": [{"message": str(e)} for e in v_errors],
                            }))
                            return
                        from graphql.execution.execute import ExecutionResult
                        result = await subscribe(schema, doc, variable_values=variables)
                        if isinstance(result, ExecutionResult):
                            # client error
                            await websocket.send(json.dumps({
                                "type": "error", "id": sid,
                                "payload": [{"message": str(e)} for e in (result.errors or [])],
                            }))
                            return
                        async for event in result:
                            await websocket.send(json.dumps({
                                "type": "next", "id": sid,
                                "payload": {"data": event.data},
                            }))
                        await websocket.send(json.dumps({"type": "complete", "id": sid}))
                    except Exception as e:
                        try:
                            await websocket.send(json.dumps({
                                "type": "error", "id": sid,
                                "payload": [{"message": str(e)}],
                            }))
                        except Exception:
                            pass

                task = asyncio.ensure_future(
                    _run_subscription(parsed["doc"], parsed["variables"], msg_id))
                subscriptions[msg_id] = task

        elif msg_type == "complete":
            # 取消订阅
            task = subscriptions.pop(msg_id, None)
            if task:
                task.cancel()

        elif msg_type == "connection_terminate":
            for t in subscriptions.values():
                t.cancel()
            return


def run_graphql_ws_server(schema, port: int = 8765, host: str = "0.0.0.0",
                          require_token: bool = False,
                          fixed_token: Optional[str] = None,
                          jsonrpc_handler: Optional[Any] = None,
                          server_name: str = "qcm-ws"):
    """启动 WebSocket 双协议服务器（graphql-ws + JSON-RPC ·）"""
    if not WEBSOCKETS_AVAILABLE:
        raise RuntimeError("需要 pip install websockets")

    async def handler(websocket):
        await _handle_ws(websocket, schema, require_token, fixed_token, jsonrpc_handler)

    async def serve():
        async with websockets.serve(handler, host, port, max_size=10 * 1024 * 1024):
            print(f"[{server_name} v1.4.0] WS 服务器启动 ws://{host}:{port}（graphql-ws + JSON-RPC 双协议）", flush=True)
            await asyncio.Future()

    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    # Demo：起一个简单 schema 的 WS server
    from graphql import build_schema, build_subscription_schema, publish_tool_event
    from graphql import GraphQLSchema

    base = build_schema(
        tools_provider=lambda: [{"name": "demo", "description": "d", "inputSchema": {}}],
        call_provider=lambda n, a: {"ok": n},
        health_provider=lambda: {"status": "ok", "version": "demo", "uptime": 1.0},
    )
    schema = GraphQLSchema(query=base.query_type, mutation=base.mutation_type,
                           subscription=build_subscription_schema())
    run_graphql_ws_server(schema, port=8769)
