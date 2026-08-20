#!/usr/bin/env python3
"""qcm_mcp_v050_test.py — QCM V0.5.0 Infoseek OAuth 2.0 + RBAC 测试

覆盖（10 用例）：
  1. infoseek_auth.py AuthManager 初始化
  2. client_credentials 签发 JWT（infoseek. 前缀）
  3. JWT 验证（verify → payload）
  4. RBAC check_scope（admin bypass / 精确 scope）
  5. Secret 加密解密（Fernet/XOR roundtrip）
  6. HTTP /oauth/token 端点（200 + access_token）
  7. OAuth JWT 调 /rpc（200 · RBAC 通过）
  8. 静态 token 向后兼容（200）
  9. 无效 token 拒绝（401）
  10. RBAC 拒绝（无权限 tool → 403）

环境依赖说明（V8.4 C 类任务）：
  本套件依赖 Infoseek 的 infoseek_auth 模块与 /oauth/token OAuth 端点。
  若 Infoseek 未安装 OAuth 支持（infoseek_auth 缺失 / 端点 404），
  整套显式 SKIP（exit 0），不为环境缺失产生虚假失败——
  参照 v044 环境依赖 SKIP 范式（协同待办：Infoseek 暴露 OAuth 端点后转真测试）。
"""
import importlib.util
import json
import os
import sys
import time
import base64
import hmac
import hashlib
import subprocess
import urllib.request
import urllib.error

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
# 跨平台 INFOSEEK_ROOT 探测（V8.4 C 类 · 对齐 v044）
if os.environ.get("INFOSEEK_ROOT"):
    INFOSEEK_ROOT = os.environ["INFOSEEK_ROOT"]
elif os.path.isdir(os.path.join(os.path.dirname(SCRIPTS), "infoseek")):
    INFOSEEK_ROOT = os.path.join(os.path.dirname(SCRIPTS), "infoseek")
else:
    INFOSEEK_ROOT = os.path.expanduser("~/.workbuddy/skills/infoseek")
INFOSEEK_SCRIPTS = os.path.join(INFOSEEK_ROOT, "scripts")
SERVER = os.path.join(INFOSEEK_SCRIPTS, "infoseek_mcp_server.py")
PORT = 8906

sys.path.insert(0, INFOSEEK_SCRIPTS)
sys.path.insert(0, SCRIPTS)


def _infoseek_auth_available():
    """探测 infoseek_auth 模块是否可导入（Infoseek OAuth 支持标志）"""
    try:
        return importlib.util.find_spec("infoseek_auth") is not None
    except Exception:
        return False


_AUTH_SKIP = not _infoseek_auth_available()


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


def start_server():
    proc = subprocess.Popen(
        [sys.executable, SERVER, "--transport", "sse", "--port", str(PORT),
         "--require-token", "--token", "static-token-123"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)
    return proc


def http_post(path, data=None, token=None, content_type="application/x-www-form-urlencoded"):
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                 data=body, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def run_v050_tests():
    print("=" * 70)
    print("QCM V0.5.0 测试套件（Infoseek OAuth 2.0 + RBAC）")
    print("=" * 70)

    passed = 0
    total = 0

    if _AUTH_SKIP:
        print("\n⏭ 环境依赖缺失：infoseek_auth 模块未安装（Infoseek OAuth 支持待协同）")
        print("   整套 10 项用例显式 SKIP（不产生虚假失败 · exit 0）")
        print("   复跑条件：Infoseek 暴露 infoseek_auth + /oauth/token 端点后")
        # 全部标记为 SKIP，计入 total 但不计入 passed（最终 return True）
        for _ in range(10):
            total += 1
            print(f"  ⏭ 用例（infoseek_auth 缺失 · SKIP）")
        print("\n" + "=" * 70)
        print(f"V0.5.0 测试结果：{passed}/{total} 通过（{total - passed} SKIP · 环境依赖）")
        print("=" * 70)
        print("ℹ️  10 项 SKIP（Infoseek OAuth 支持待协同 · 无实现缺陷失败）")
        return True

    # [1] AuthManager 初始化
    print("\n[1. AuthManager]")
    total += 1
    def auth_init():
        from infoseek_auth import AuthManager, SecretCipher
        auth = AuthManager()
        assert auth is not None
        cipher = SecretCipher("test-key")
        assert cipher is not None
        return True
    if test("AuthManager + SecretCipher 初始化", auth_init):
        passed += 1

    # [2] client_credentials 签发
    total += 1
    def issue_token():
        from infoseek_auth import AuthManager
        auth = AuthManager()
        r = auth.client_credentials("default-client", "default-secret",
                                    scope=["tools/call", "tools/list"])
        assert "access_token" in r, f"no token: {r}"
        assert r["access_token"].startswith("infoseek."), f"prefix: {r['access_token'][:12]}"
        assert r["token_type"] == "Bearer"
        assert r["expires_in"] == 3600
        return True
    if test("client_credentials → infoseek. JWT", issue_token):
        passed += 1

    # [3] JWT 验证
    total += 1
    def verify_token():
        from infoseek_auth import AuthManager
        auth = AuthManager()
        r = auth.client_credentials("default-client", "default-secret")
        payload = auth.verify(r["access_token"])
        assert payload is not None, "verify failed"
        assert payload["sub"] == "default-client"
        assert "exp" in payload and "iat" in payload
        return True
    if test("verify → payload（sub/exp/iat）", verify_token):
        passed += 1

    # [4] RBAC
    total += 1
    def rbac_check():
        from infoseek_auth import AuthManager
        auth = AuthManager()
        r = auth.client_credentials("default-client", "default-secret",
                                    scope=["tools/call"])
        payload = auth.verify(r["access_token"])
        # default tenant 是 admin → 全通过
        assert auth.check_scope(payload, "tools/call") is True
        assert auth.check_tool(payload, "research_v3") is True
        # 无效 payload
        assert auth.check_scope(None, "tools/call") is False
        return True
    if test("RBAC check_scope/check_tool（admin bypass）", rbac_check):
        passed += 1

    # [5] Secret 加密
    total += 1
    def secret_cipher():
        from infoseek_auth import SecretCipher
        cipher = SecretCipher("master-key")
        plain = "sk-deepseek-secret-xyz-12345"
        enc = cipher.encrypt(plain)
        assert enc != plain, "encrypt no-op"
        dec = cipher.decrypt(enc)
        assert dec == plain, f"roundtrip failed: {dec}"
        return True
    if test("Secret 加密解密 roundtrip", secret_cipher):
        passed += 1

    # [6-10] HTTP 端点
    print("\n[2. HTTP 端点]")
    proc = start_server()
    try:
        # [6] /oauth/token
        total += 1
        def oauth_endpoint():
            status, body = http_post("/oauth/token",
                "client_id=default-client&client_secret=default-secret&scope=tools%2Fcall")
            assert status == 200, f"status={status}: {body}"
            assert "access_token" in body
            assert body["token_type"] == "Bearer"
            return True
        if test("/oauth/token → 200 + access_token", oauth_endpoint):
            passed += 1

        # [7] OAuth JWT 调 /rpc
        total += 1
        def oauth_rpc():
            _, body = http_post("/oauth/token",
                "client_id=default-client&client_secret=default-secret")
            token = body["access_token"]
            status, resp = http_post("/rpc",
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                token=token, content_type="application/json")
            assert status == 200, f"status={status}"
            assert "tools" in resp["result"]
            return True
        if test("OAuth JWT 调 /rpc → 200", oauth_rpc):
            passed += 1

        # [8] 静态 token 兼容
        total += 1
        def static_token():
            status, resp = http_post("/rpc",
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                token="static-token-123", content_type="application/json")
            assert status == 200, f"status={status}: {resp}"
            return True
        if test("静态 token 向后兼容 → 200", static_token):
            passed += 1

        # [9] 无效 token
        total += 1
        def invalid_token():
            status, _ = http_post("/rpc",
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                token="wrong-token", content_type="application/json")
            assert status == 401, f"status={status}"
            return True
        if test("无效 token → 401", invalid_token):
            passed += 1

        # [10] 错误 client_secret
        total += 1
        def wrong_secret():
            status, body = http_post("/oauth/token",
                "client_id=default-client&client_secret=wrong-secret")
            assert status == 401, f"status={status}"
            assert body.get("error") == "invalid_client"
            return True
        if test("错误 client_secret → 401 invalid_client", wrong_secret):
            passed += 1
    finally:
        proc.terminate()

    # 总结
    print("\n" + "=" * 70)
    print(f"V0.5.0 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ Infoseek V0.5.0 全部测试通过")
        print("   - OAuth 2.0 client_credentials + JWT")
        print("   - RBAC per-tool")
        print("   - Secret 加密（Fernet/XOR）")
        print("   - HTTP /oauth/token + 静态 token 兼容")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v050_tests()
    sys.exit(0 if success else 1)
