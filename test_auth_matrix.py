
import requests

BASE_URL = "http://localhost:8000"

def test_login(email, password, requested_role, expected_status):
    print(f"Testing login for {email} as {requested_role}...")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password,
        "role": requested_role
    })
    
    assert res.status_code == expected_status, f"Expected {expected_status}, got {res.status_code}. Response: {res.text}"
    if res.status_code == 200:
        print(" -> Success (Token received)")
        return res.json()["access_token"]
    else:
        print(f" -> Failed as expected: {res.json().get('detail')}")
        return None

def test_protected_route(token, expected_status):
    print(f"Testing protected /police/extract-statement with token...")
    res = requests.post(f"{BASE_URL}/police/extract-statement", json={"statement": "Test"}, headers={
        "Authorization": f"Bearer {token}"
    })
    assert res.status_code == expected_status, f"Expected {expected_status}, got {res.status_code}. Response: {res.text}"
    print(f" -> Success, got {res.status_code}")

print("--- Testing Auth Matrix ---")
# 1. Citizen logs in as Citizen
cit_token = test_login("citizen@lawaid.com", "password123", "citizen", 200)

# 2. Citizen logs in as Police (Should fail with 403)
test_login("citizen@lawaid.com", "password123", "police", 403)

# 3. Police logs in as Police
pol_token = test_login("police@lawaid.com", "password123", "police", 200)

# 4. Citizen tries to access Police protected route (Should fail with 403)
test_protected_route(cit_token, 403)

# 5. Police tries to access Police protected route (Should succeed with 200)
test_protected_route(pol_token, 200)

print("All backend auth tests passed!")

