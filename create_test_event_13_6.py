"""Create test event and upload media for Phase 13.6 browser verification."""
import requests
import time
import os

BASE = "http://localhost"
IMG_DIR = r"C:\Users\Person\Desktop\GALL\test_images_13_6"

# Login as admin
r = requests.post(f"{BASE}/api/auth/login", json={"email": "admin@lentisevent.gallery", "password": "Lordlentis1972"})
r.raise_for_status()
admin_token = r.json()["access_token"]["access_token"]
headers = {"Authorization": f"Bearer {admin_token}"}

# Create event
r = requests.post(f"{BASE}/api/events", headers=headers, json={
    "name": "Phase 13.6 Slideshow Test",
    "subtitle": "Testing hero slideshow, landing slideshow, guest slideshow, host slideshow, and gallery separation",
    "host_name": "Test Host",
    "host_email": "testhost136@lentisevent.gallery",
    "host_password": "TestHost136",
    "event_date": "2026-09-01",
    "slug": "phase-13-6-test",
})
r.raise_for_status()
event = r.json()
event_id = event["id"]
print(f"Event created: {event_id}")

# Set event to LIVE
r = requests.patch(f"{BASE}/api/admin/events/{event_id}", headers=headers, json={"status": "LIVE"})
r.raise_for_status()
print("Event set to LIVE")

# Define uploads: (filename, role, page)
UPLOADS = [
    ("hero_1.png", "HERO", "LANDING"),
    ("hero_2.png", "HERO", "LANDING"),
    ("hero_3.png", "HERO", "LANDING"),
    ("slide_l_1.png", "SLIDESHOW", "LANDING"),
    ("slide_l_2.png", "SLIDESHOW", "LANDING"),
    ("slide_l_3.png", "SLIDESHOW", "LANDING"),
    ("slide_g_1.png", "SLIDESHOW", "GUEST"),
    ("slide_g_2.png", "SLIDESHOW", "GUEST"),
    ("slide_g_3.png", "SLIDESHOW", "GUEST"),
    ("slide_h_1.png", "HOST_SLIDESHOW", "HOST"),
    ("slide_h_2.png", "HOST_SLIDESHOW", "HOST"),
    ("slide_h_3.png", "HOST_SLIDESHOW", "HOST"),
    ("gallery_1.png", "GALLERY", None),
    ("gallery_2.png", "GALLERY", None),
]

# Upload all images
for filename, role, page in UPLOADS:
    filepath = os.path.join(IMG_DIR, filename)
    with open(filepath, "rb") as f:
        data = {"file": (filename, f, "image/png")}
        form_data = {
            "media_role": role,
            "source": "ADMIN",
        }
        if page:
            form_data["page"] = page
        
        r = requests.post(
            f"{BASE}/api/admin/events/{event_id}/media",
            headers=headers,
            files=data,
            data=form_data,
        )
        if r.status_code == 200:
            print(f"  Uploaded {filename} -> {role}/{page or 'null'}")
        else:
            print(f"  FAILED {filename}: {r.status_code} {r.text[:100]}")
    time.sleep(0.3)

# Verify: get public media
r = requests.get(f"{BASE}/api/events/phase-13-6-test/public-media")
if r.status_code == 200:
    media = r.json()
    print(f"\nPublic media verification:")
    print(f"  Hero: {len(media['hero'])} items")
    print(f"  Slideshow (landing): {len(media['slideshow'])} items")
    print(f"  Guest slideshow: {len(media['guest_slideshow'])} items")
    print(f"  Gallery: {len(media['gallery'])} items")
else:
    print(f"  FAILED to get public media: {r.status_code}")

# Get admin media list
r = requests.get(f"{BASE}/api/admin/events/{event_id}/media", headers=headers)
if r.status_code == 200:
    items = r.json()["items"]
    print(f"\nAdmin media list: {len(items)} items")
    for m in items:
        print(f"  {m['original_filename']}: role={m['media_role']}, page={m.get('page')}, source={m['source']}")

print(f"\nTest event URL: http://localhost/e/phase-13-6-test")
