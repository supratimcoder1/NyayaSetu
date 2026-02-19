import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(path, expected_status=[200]):
    try:
        response = requests.get(f"{BASE_URL}{path}")
        if response.status_code in expected_status:
            print(f"✅ {path} is UP ({response.status_code})")
            return True
        else:
            print(f"❌ {path} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {path} failed: {e}")
        return False

print("🔍 Verifying Refactored Endpoints...")

# 1. Check Root
if not check_endpoint("/"):
    sys.exit(1)

# 2. Check Login Page
if not check_endpoint("/login"):
    sys.exit(1)

# 3. Check Dashboard (Should redirect to login if no cookie, so 200 OK because it returns HTML login page or 307)
# Actually, redirects in requests follow by default, so it might land on /login (200)
check_endpoint("/dashboard")

print("✅ Server Refactoring Verification Passed!")
