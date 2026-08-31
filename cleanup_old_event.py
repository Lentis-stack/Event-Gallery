import requests

BASE = "http://localhost"
r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@lentisevent.gallery", "password": "Lordlentis1972"})
token = r.json()["access_token"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Delete old test event
r = requests.get(f"{BASE}/api/admin/events", headers=headers)
events = r.json()
for ev in events:
    if ev.get("slug") == "phase-13-6-test":
        eid = ev["id"]
        requests.delete(f"{BASE}/api/admin/events/{eid}", headers=headers)
        print(f"Deleted old event: {eid}")
        break
