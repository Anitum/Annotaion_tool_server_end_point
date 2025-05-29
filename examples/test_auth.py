import requests
import json

BASE_URL = "http://localhost:5000"

def test_no_auth():
    """Test endpoint without authentication"""
    print("🔍 Testing without API key...")
    response = requests.get(f"{BASE_URL}/query/local")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401
    print("✅ Correctly rejected unauthenticated request\n")

def test_invalid_auth():
    """Test with invalid API key"""
    print("🔍 Testing with invalid API key...")
    headers = {'X-API-Key': 'invalid_key_123'}
    response = requests.get(f"{BASE_URL}/query/local", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401
    print("✅ Correctly rejected invalid API key\n")

def test_valid_auth_x_api_key():
    """Test with valid API key using X-API-Key header"""
    print("🔍 Testing with valid X-API-Key...")
    headers = {'X-API-Key': 'sk_live_abc123def456ghi789jkl012mno345pqr678'}
    response = requests.get(f"{BASE_URL}/query/local", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response keys: {list(response.json().keys())}")
    assert response.status_code == 200
    print("✅ Successfully authenticated with X-API-Key\n")

def test_valid_auth_bearer():
    """Test with valid API key using Authorization Bearer"""
    print("🔍 Testing with valid Bearer token...")
    headers = {'Authorization': 'Bearer sk_live_abc123def456ghi789jkl012mno345pqr678'}
    response = requests.get(f"{BASE_URL}/query/local", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response keys: {list(response.json().keys())}")
    assert response.status_code == 200
    print("✅ Successfully authenticated with Bearer token\n")

def test_public_endpoint():
    """Test public endpoint (no auth required)"""
    print("🔍 Testing public endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Public endpoint works without auth\n")

def test_generate_key():
    """Test API key generation"""
    print("🔍 Testing API key generation...")
    response = requests.post(f"{BASE_URL}/auth/generate-key")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Generated key: {data.get('api_key', 'None')[:20]}...")
    assert response.status_code == 200
    assert 'api_key' in data
    print("✅ Successfully generated new API key\n")

if __name__ == "__main__":
    print("🔐 Authentication Testing\n")
    
    test_public_endpoint()
    test_no_auth()
    test_invalid_auth()
    test_valid_auth_x_api_key()
    test_valid_auth_bearer()
    test_generate_key()
    
    print("🎉 All authentication tests passed!")
