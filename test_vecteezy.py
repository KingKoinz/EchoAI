"""Test Vecteezy API credentials and quota"""
import requests
import yaml

CONFIG_PATH = "config/settings.yaml"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

api_key = config.get("vecteezy", {}).get("api_key", "")
account_id = config.get("vecteezy", {}).get("account_id", "")

print(f"API Key: {api_key[:20]}...")
print(f"Account ID: {account_id}\n")

# Test 1: Account Info
print("=" * 60)
print("TEST 1: Account Info & Quota")
print("=" * 60)
quota_url = f"https://api.vecteezy.com/v2/{account_id}/account/info"
headers = {"Authorization": f"Bearer {api_key}"}

try:
    r = requests.get(quota_url, headers=headers, timeout=10)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}\n")
    
    if r.status_code == 200:
        data = r.json()
        print("Parsed Data:")
        for key, value in data.items():
            print(f"  {key}: {value}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Search for images
print("\n" + "=" * 60)
print("TEST 2: Search for 'lifestyle' photos")
print("=" * 60)
search_url = f"https://api.vecteezy.com/v2/{account_id}/resources"
params = {
    "query": "lifestyle",
    "resource_type": "photo",
    "license": "free",
    "orientation": "portrait",
    "page": 1,
    "limit": 5
}

try:
    r = requests.get(search_url, headers=headers, params=params, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        resources = data.get("data", [])
        print(f"Found {len(resources)} results")
        
        if resources:
            print("\nFirst result:")
            first = resources[0]
            print(f"  ID: {first.get('id')}")
            print(f"  Title: {first.get('title')}")
            print(f"  Type: {first.get('resource_type')}")
    else:
        print(f"Error Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
