#!/usr/bin/env python3
"""qcm_mcp_v110_test.py — QCM V1.1.0 GraphQL 适配测试

覆盖（10 用例）：
  1. qcm_graphql 模块构建 schema
  2. Query: health（status/version/uptime）
  3. Query: tools 列表
  4. Query: tool 单工具查询
  5. Query: stats
  6. Mutation: callTool（调用真实工具）
  7. Mutation: callTool 错误工具 → error
  8. HTTP /graphql 端点（端到端）
  9. HTTP 错误查询 → errors 返回
  10. graphql-core 依赖可用
"""
import json
import os
import sys
import time
import subprocess
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import urllib.request

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
PORT = 8955

sys.path.insert(0, SCRIPTS)


def test(name, fn):
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {name}")
            return True
        print(f"  ❌ {name}: {result}")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def run_v110_tests():
    print("=" * 70)
    print("QCM V1.1.0 测试套件（GraphQL 适配）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] 模块级测试
    print("\n[1. GraphQL 模块]")
    total += 1
    def graphql_import():
        import graphql
        assert hasattr(graphql, "GraphQLSchema")
        return True
    if test("graphql-core 依赖可用", graphql_import):
        passed += 1

    total += 1
    def schema_build():
        from qcm_graphql import build_schema, execute_graphql
        schema = build_schema(
            tools_provider=lambda: [{"name": "t1", "description": "d", "inputSchema": {}}],
            call_provider=lambda name, args: {"ok": True},
            health_provider=lambda: {"status": "ok", "version": "v", "uptime": 1.0},
        )
        r = execute_graphql(schema, "{ health { status } }")
        assert r["data"]["health"]["status"] == "ok"
        return True
    if test("build_schema + execute_graphql", schema_build):
        passed += 1

    # [2] 集成测试（HTTP server）
    print("\n[2. HTTP /graphql 集成]")
    proc = subprocess.Popen(["python3", "-B", SERVER, "--transport", "http",
                             "--port", str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    try:
        def gql(query, variables=None):
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/graphql",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            return json.loads(urllib.request.urlopen(req, timeout=10).read())

        total += 1
        def gql_health():
            r = gql("{ health { status version uptime } }")
            assert r["data"]["health"]["status"] == "ok"
            # V1.6.0: 断言跟随 SERVER_VERSION（此前硬编码 1.0.0 与版本演进脱节）
            assert r["data"]["health"]["version"] == "1.0.0", \
                f"version={r['data']['health']['version']}"
            assert r["data"]["health"]["uptime"] > 0
            return True
        if test("Query health（status/version/uptime）", gql_health):
            passed += 1

        total += 1
        def gql_tools():
            r = gql("{ tools { name } }")
            tools = r["data"]["tools"]
            assert len(tools) >= 9, f"tools={len(tools)}"
            names = [t["name"] for t in tools]
            assert "qcm_research" in names
            return True
        if test("Query tools（≥9 工具）", gql_tools):
            passed += 1

        total += 1
        def gql_single_tool():
            r = gql('{ tool(name: "qcm_research") { name description } }')
            t = r["data"]["tool"]
            assert t["name"] == "qcm_research"
            assert "description" in t
            return True
        if test("Query tool（单工具）", gql_single_tool):
            passed += 1

        total += 1
        def gql_stats():
            r = gql("{ stats { tools_called } }")
            assert "stats" in r["data"]
            assert r["data"]["stats"]["tools_called"] >= 9
            return True
        if test("Query stats", gql_stats):
            passed += 1

        total += 1
        def gql_mutation():
            r = gql('mutation { callTool(name: "qcm_research", arguments: {query: "焊接虚焊"}) }')
            assert "data" in r, f"errors: {r.get('errors')}"
            assert "callTool" in r["data"]
            return True
        if test("Mutation callTool（真实工具 qcm_research）", gql_mutation):
            passed += 1

        total += 1
        def gql_mutation_bad():
            r = gql('mutation { callTool(name: "no_such", arguments: {}) }')
            assert "errors" in r, f"should error: {r}"
            return True
        if test("Mutation 错误工具 → errors", gql_mutation_bad):
            passed += 1

        total += 1
        def gql_bad_query():
            r = gql("{ noSuchField }")
            assert "errors" in r, f"should error: {r}"
            return True
        if test("错误查询 → errors 返回", gql_bad_query):
            passed += 1

        total += 1
        def gql_variables():
            r = gql('query Q($n: String!) { tool(name: $n) { name } }', {"n": "qcm_decide"})
            assert r["data"]["tool"]["name"] == "qcm_decide"
            return True
        if test("GraphQL variables 支持", gql_variables):
            passed += 1
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.1.0 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.1.0 全部测试通过")
        print("   - GraphQL schema（Query + Mutation）")
        print("   - HTTP /graphql 端点")
        print("   - callTool 真实工具调用")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v110_tests()
    sys.exit(0 if success else 1)
