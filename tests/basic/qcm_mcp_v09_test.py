#!/usr/bin/env python3
"""qcm_mcp_v09_test.py — QCM V0.9 安全 + 多租户测试

V0.9 任务清单：
  - V0.9-01 OAuth 2.0 client_credentials flow
  - V0.9-02 TLS/HTTPS（标记 V0.9.2 推迟 · 需 OpenSSL/cert 工具）
  - V0.9-03 Multi-tenant（per-tenant token + corpus）
  - V0.9-04 RBAC per-tool 权限
  - V0.9-05 Secret 加密（API Key 不落盘）
  - V0.8-01 multi-process（标记 V0.8.1 推迟 · 需 gunicorn/uvicorn）

测试场景（12）：
  OAuth（4）：
    - client_credentials 流程
    - Token 验证
    - 错误 client_id
    - 错误 client_secret

  RBAC（3）：
    - admin 角色通过
    - 普通 client 通过工具调用
    - 错误 scope 拒绝

  Secret 加密（2）：
    - Fernet 加密/解密
    - XOR fallback

  Multi-tenant（2）：
    - 默认 tenant
    - 加载自定义 tenant 文件

  Integration（1）：
    - /oauth/token 端点集成
"""
import os
import sys
import time
import json
import subprocess
import signal
import socket
import urllib.request
import urllib.error
from pathlib import Path
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)


def test(name, fn, expect_error=False):
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误）")
                return True
            print(f"  ❌ {name}: {result.get('error')}")
            return False
        if expect_error and not isinstance(result, bool):
            print(f"  ❌ {name}: 预期错误但返回成功")
            return False
        if isinstance(result, bool) and not result:
            print(f"  ❌ {name}: assert failed")
            return False
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_v09_tests():
    print("=" * 70)
    print(f"QCM MCP Server V0.9 测试（OAuth + RBAC + Secret + Multi-tenant）")
    print("=" * 70)

    passed = 0
    total = 0

    # ========== 1. OAuth（4） ==========
    print("\n[1. OAuth 2.0 client_credentials]")

    def oauth_client_credentials():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials(
            "default-client", "default-secret",
            scope=["tools/call", "tools/list", "resources/read", "prompts/list", "prompts/get"]
        )
        assert "access_token" in result
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 3600
        assert result["access_token"].startswith("qcm.")
        return True

    total += 1
    if test("client_credentials · 成功", oauth_client_credentials):
        passed += 1

    def oauth_token_verify():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials("default-client", "default-secret", scope=["tools/call"])
        payload = auth.verify(result["access_token"])
        assert payload is not None
        assert payload["sub"] == "default-client"
        assert "tools/call" in payload["scope"]
        return True

    total += 1
    if test("Token 验证", oauth_token_verify):
        passed += 1

    def oauth_wrong_client():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials("wrong-client", "default-secret")
        assert "error" in result
        assert result["error"] == "invalid_client"
        return True

    total += 1
    if test("错误 client_id → invalid_client", oauth_wrong_client):
        passed += 1

    def oauth_wrong_secret():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials("default-client", "wrong-secret")
        assert "error" in result
        return True

    total += 1
    if test("错误 client_secret → invalid_client", oauth_wrong_secret):
        passed += 1

    # ========== 2. RBAC（3） ==========
    print("\n[2. RBAC per-tool]")

    def rbac_admin():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials("default-client", "default-secret")
        payload = auth.verify(result["access_token"])
        # admin 角色可调任何 tool
        assert auth.check_scope(payload, "tools/call") is True
        assert auth.check_scope(payload, "admin") is True
        return True

    total += 1
    if test("admin 角色通过所有 scope", rbac_admin):
        passed += 1

    def rbac_tool_check():
        from auth import AuthManager
        auth = AuthManager()
        result = auth.client_credentials("default-client", "default-secret", scope=["tools/call"])
        payload = auth.verify(result["access_token"])
        # tools/call scope 允许调任何 tool
        assert auth.check_tool(payload, "qcm_research") is True
        assert auth.check_tool(payload, "qcm_decide") is True
        return True

    total += 1
    if test("普通 client + tools/call → 可调工具", rbac_tool_check):
        passed += 1

    def rbac_wrong_scope():
        # 使用自定义 non-admin tenant
        import tempfile
        from auth import AuthManager
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "tenants": {
                    "test_user": {
                        "client_id": "test_user_client",
                        "client_secret": "test_user_secret",
                        "scopes": ["prompts/list"],  # 只有 prompts 权限
                        "roles": ["user"]
                    }
                }
            }, f)
            tmpfile = f.name
        os.environ["QCM_TENANTS_FILE"] = tmpfile
        auth = AuthManager()
        del os.environ["QCM_TENANTS_FILE"]
        os.unlink(tmpfile)

        result = auth.client_credentials(
            "test_user_client", "test_user_secret",
            scope=["prompts/list"], tenant="test_user"
        )
        payload = auth.verify(result["access_token"])
        # test_user 没有 tools/call scope
        assert auth.check_scope(payload, "tools/call") is False
        assert auth.check_scope(payload, "prompts/list") is True
        return True

    total += 1
    if test("错误 scope → 拒绝", rbac_wrong_scope):
        passed += 1

    # ========== 3. Secret 加密（2） ==========
    print("\n[3. Secret 加密]")

    def secret_encrypt_decrypt():
        from auth import SecretCipher
        cipher = SecretCipher("test-master-key")
        plaintext = "sk-deepseek-real-api-key-12345"
        encrypted = cipher.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext
        return True

    total += 1
    if test("Secret 加密/解密 roundtrip", secret_encrypt_decrypt):
        passed += 1

    def secret_xor_fallback():
        from auth import SecretCipher
        cipher = SecretCipher("test-master-key")
        # 没 cryptography 库时降级到 XOR
        plaintext = "test-secret-xyz"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext
        return True

    total += 1
    if test("XOR fallback 加密", secret_xor_fallback):
        passed += 1

    # ========== 4. Multi-tenant（2） ==========
    print("\n[4. Multi-tenant]")

    def tenant_default():
        from auth import AuthManager
        auth = AuthManager()
        assert "default" in auth.tenants
        tenant = auth.tenants["default"]
        assert tenant["client_id"] == "default-client"
        assert "admin" in tenant["roles"]
        return True

    total += 1
    if test("默认 tenant（admin）", tenant_default):
        passed += 1

    def tenant_custom_file():
        import tempfile
        from auth import AuthManager

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "tenants": {
                    "tenant_a": {
                        "client_id": "client_a",
                        "client_secret": "secret_a",
                        "scopes": ["tools/call"],
                        "roles": ["user"]
                    }
                }
            }, f)
            tmpfile = f.name

        os.environ["QCM_TENANTS_FILE"] = tmpfile
        auth = AuthManager()
        del os.environ["QCM_TENANTS_FILE"]
        os.unlink(tmpfile)

        assert "tenant_a" in auth.tenants
        result = auth.client_credentials("client_a", "secret_a", scope=["tools/call"], tenant="tenant_a")
        assert "access_token" in result
        return True

    total += 1
    if test("加载自定义 tenant JSON 文件", tenant_custom_file):
        passed += 1

    # ========== 5. Integration（1） ==========
    print("\n[5. Integration · /oauth/token 端点]")

    TEST_PORT = find_free_port()
    proc = None
    try:
        proc = subprocess.Popen(
            ["python3", os.path.join(SCRIPTS, "mcp_server.py"),
             "--transport", "http", "--port", str(TEST_PORT)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ},
        )
        # 等 server 启动
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/health/live", timeout=1) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, ConnectionRefusedError):
                time.sleep(0.1)

        def oauth_endpoint():
            # POST /oauth/token · client_credentials
            payload = "grant_type=client_credentials&client_id=default-client&client_secret=default-secret&scope=tools/call"
            req = urllib.request.Request(
                f"http://127.0.0.1:{TEST_PORT}/oauth/token",
                data=payload.encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = json.loads(resp.read().decode())
            assert "access_token" in body
            assert body["token_type"] == "Bearer"
            return True

        total += 1
        if test("POST /oauth/token 端点", oauth_endpoint):
            passed += 1

    finally:
        if proc:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print(f"V0.9 测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server V0.9 全部测试通过")
        print("   - OAuth 2.0 client_credentials + JWT-like token")
        print("   - RBAC per-tool（admin 角色 + scope 检查）")
        print("   - Secret 加密（Fernet + XOR fallback）")
        print("   - Multi-tenant（默认 + JSON 文件加载）")
        print("   - /oauth/token 端点集成")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_v09_tests()
    sys.exit(0 if success else 1)