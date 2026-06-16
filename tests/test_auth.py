import requests

BASE = "http://localhost:8000"

# 1. Register
print("=== Register ===")
r = requests.post(f"{BASE}/auth/register", json={"username": "demo2", "password": "demo123"})
print(f"  {r.status_code}: {r.text}")

# 2. Login
print("\n=== Login ===")
r = requests.post(f"{BASE}/auth/login", json={"username": "demo2", "password": "demo123"})
print(f"  {r.status_code}: {r.text[:80]}...")
data = r.json()
token = data["access_token"]
print(f"  Full token length: {len(token)}")
print(f"  Token starts with: {token[:30]}...")

# 3. Get Me
print("\n=== Get Me ===")
headers = {"Authorization": f"Bearer {token}"}
r = requests.get(f"{BASE}/auth/me", headers=headers)
print(f"  {r.status_code}: {r.text}")

# 4. History (empty)
print("\n=== History ===")
r = requests.get(f"{BASE}/history", headers=headers)
print(f"  {r.status_code}: {r.text}")

# 5. No token
print("\n=== No Token ===")
r = requests.get(f"{BASE}/history")
print(f"  {r.status_code}: {r.text}")

print("\nDone!")
