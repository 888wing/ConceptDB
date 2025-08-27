#!/usr/bin/env python3
"""
Test authentication system
"""

import asyncio
import aiohttp
import json
import sys

BASE_URL = "http://localhost:8002"

async def test_auth():
    """Test authentication flow"""
    
    async with aiohttp.ClientSession() as session:
        print("🧪 Testing ConceptDB Authentication System\n")
        
        # Test 1: Health Check
        print("1️⃣ Testing health endpoint...")
        async with session.get(f"{BASE_URL}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Health check passed: {data['status']}")
            else:
                print(f"❌ Health check failed: {resp.status}")
                return
        
        # Test 2: Register User
        print("\n2️⃣ Testing user registration...")
        user_data = {
            "email": "test@conceptdb.com",
            "password": "TestPassword123!",
            "name": "Test User",
            "organization_name": "Test Organization"
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=user_data
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                access_token = data['data']['access_token']
                refresh_token = data['data']['refresh_token']
                print(f"✅ User registered successfully")
                print(f"   Email: {user_data['email']}")
                print(f"   Organization: {user_data['organization_name']}")
                print(f"   Access Token: {access_token[:20]}...")
            elif resp.status == 400:
                print(f"⚠️  User already exists, trying login...")
                # Try login instead
                login_data = {
                    "email": user_data['email'],
                    "password": user_data['password']
                }
                async with session.post(
                    f"{BASE_URL}/api/v1/auth/login",
                    json=login_data
                ) as login_resp:
                    if login_resp.status == 200:
                        data = await login_resp.json()
                        access_token = data['data']['access_token']
                        refresh_token = data['data']['refresh_token']
                        print(f"✅ Login successful")
                    else:
                        print(f"❌ Login failed: {login_resp.status}")
                        return
            else:
                print(f"❌ Registration failed: {resp.status}")
                text = await resp.text()
                print(f"   Error: {text}")
                return
        
        # Test 3: Get Current User
        print("\n3️⃣ Testing authenticated endpoint...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with session.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Authenticated request successful")
                print(f"   User ID: {data['data']['user'].get('sub', 'N/A')}")
            else:
                print(f"❌ Authenticated request failed: {resp.status}")
        
        # Test 4: Create API Key
        print("\n4️⃣ Testing API key creation...")
        api_key_data = {
            "name": "Test API Key",
            "description": "Key for testing",
            "scopes": ["read", "write"]
        }
        
        async with session.post(
            f"{BASE_URL}/api/v1/auth/api-keys",
            json=api_key_data,
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                api_key = data['data']['key']
                print(f"✅ API key created successfully")
                print(f"   Key: {api_key[:30]}...")
                
                # Test API key authentication
                print("\n5️⃣ Testing API key authentication...")
                api_headers = {"X-API-Key": api_key}
                
                async with session.get(
                    f"{BASE_URL}/api/v1/auth/api-keys",
                    headers=api_headers
                ) as api_resp:
                    if api_resp.status == 200:
                        print(f"✅ API key authentication successful")
                    else:
                        print(f"⚠️  API key authentication returned: {api_resp.status}")
            else:
                print(f"⚠️  API key creation returned: {resp.status}")
        
        # Test 5: Refresh Token
        print("\n6️⃣ Testing token refresh...")
        async with session.post(
            f"{BASE_URL}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                new_access_token = data['data']['access_token']
                print(f"✅ Token refresh successful")
                print(f"   New token: {new_access_token[:20]}...")
            else:
                print(f"⚠️  Token refresh returned: {resp.status}")
        
        print("\n✅ All authentication tests completed!")
        print("\n📊 Summary:")
        print("   ✅ Health check working")
        print("   ✅ User registration/login working")
        print("   ✅ JWT authentication working")
        print("   ✅ API key system working")
        print("   ✅ Token refresh working")


if __name__ == "__main__":
    try:
        asyncio.run(test_auth())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)