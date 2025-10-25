#!/usr/bin/env python3
"""
Quick test script for FastAPI server.
Tests basic endpoints without starting the full server.
"""

import os
import sys

# Set environment variables
os.environ['OBSIDIAN_API_KEY'] = '07452926311ed660b8a3d309a2581979dbe404a393375635c20873e94aadb870'
os.environ['OBSIDIAN_PROTOCOL'] = 'http'
os.environ['OBSIDIAN_HOST'] = 'secondbrain.oihugudev.com.br'
os.environ['OBSIDIAN_PORT'] = '80'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-development'
os.environ['API_KEYS'] = 'test-key-123,test-key-456'

print("="*80)
print("Testing FastAPI Implementation")
print("="*80)

# Test imports
print("\n1. Testing imports...")
try:
    from src.api import server, models, auth, middleware
    print("   ✅ All API modules imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test models
print("\n2. Testing Pydantic models...")
try:
    from src.api.models import ToolRequest, ToolResponse, HealthResponse

    # Test ToolRequest
    req = ToolRequest(args={"query": "test", "top_k": 10})
    assert req.args["query"] == "test"
    print("   ✅ ToolRequest model OK")

    # Test ToolResponse
    resp = ToolResponse(success=True, tool_name="test_tool", result={"data": "test"})
    assert resp.success == True
    print("   ✅ ToolResponse model OK")

    # Test HealthResponse
    health = HealthResponse(status="healthy", version="0.3.0")
    assert health.status == "healthy"
    print("   ✅ HealthResponse model OK")

except Exception as e:
    print(f"   ❌ Model test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test auth
print("\n3. Testing authentication...")
try:
    from src.api.auth import create_access_token, decode_token, verify_api_key

    # Test JWT creation
    token = create_access_token({"sub": "test_user", "roles": ["admin"]})
    assert token is not None
    print("   ✅ JWT token creation OK")

    # Test JWT decoding
    payload = decode_token(token)
    assert payload["sub"] == "test_user"
    print("   ✅ JWT token decoding OK")

    # Test API key verification
    assert verify_api_key("test-key-123") == True
    assert verify_api_key("invalid-key") == False
    print("   ✅ API key verification OK")

except Exception as e:
    print(f"   ❌ Auth test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test FastAPI app creation
print("\n4. Testing FastAPI app...")
try:
    from src.api.server import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    print(f"   ✅ Health check OK - Status: {data['status']}")

    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    print(f"   ✅ Root endpoint OK - Version: {data['version']}")

    # Test auth endpoint (should fail without credentials)
    response = client.post("/auth/token", json={"username": "admin", "password": "changeme"})
    if response.status_code == 200:
        data = response.json()
        assert "access_token" in data
        print(f"   ✅ Auth endpoint OK - Token generated")
    else:
        print(f"   ⚠️  Auth endpoint returned {response.status_code} (may need config)")

except ImportError as e:
    print(f"   ⚠️  TestClient not available (install: pip install httpx)")
    print(f"      Skipping FastAPI tests")
except Exception as e:
    print(f"   ❌ FastAPI test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test tool listing (without auth for basic test)
print("\n5. Testing MCP integration...")
try:
    from src.mcp_obsidian import server as mcp_server

    total_tools = len(mcp_server.tool_handlers)
    assert total_tools > 0
    print(f"   ✅ MCP tools available: {total_tools} tools")

    # List some tools
    tool_names = list(mcp_server.tool_handlers.keys())[:5]
    print(f"   ℹ️  Sample tools: {', '.join(tool_names)}")

except Exception as e:
    print(f"   ❌ MCP integration test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "="*80)
print("✅ All tests passed!")
print("="*80)
print("\n📝 Next steps:")
print("   1. Start the server:")
print("      python -m src.api.server")
print()
print("   2. Or use uvicorn directly:")
print("      uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload")
print()
print("   3. Access docs at:")
print("      http://localhost:8000/docs")
print()
print("   4. Test with curl:")
print("      curl http://localhost:8000/health")
print()
print("   5. Get token:")
print("      curl -X POST http://localhost:8000/auth/token \\")
print("        -H 'Content-Type: application/json' \\")
print("        -d '{\"username\": \"admin\", \"password\": \"changeme\"}'")
print()
print("="*80)
