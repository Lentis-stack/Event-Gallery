import requests
r = requests.get("http://localhost/api/events/phase-13-6-test/public-media")
print("Status:", r.status_code)
if r.status_code == 200:
    d = r.json()
    print("Hero:", len(d["hero"]), "items")
    print("Slideshow:", len(d["slideshow"]), "items")
    print("Guest slideshow:", len(d["guest_slideshow"]), "items")
    print("Gallery:", len(d["gallery"]), "items")
    for h in d["hero"]:
        print(f"  Hero: {h['alt']}")
    for s in d["slideshow"]:
        print(f"  Landing: {s['alt']}")
    for g in d["guest_slideshow"]:
        print(f"  Guest: {g['alt']}")
else:
    print(r.text[:200])
