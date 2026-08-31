# Cloudflare DNS Setup — lentisevent.gallery

This guide covers configuring DNS for Lentis Event Gallery using Cloudflare.

---

## Prerequisites

- A Cloudflare account (free plan is sufficient)
- Access to the domain registrar for `lentisevent.gallery`
- The production server IP: `105.119.10.250`

---

## Step 1: Add the Domain to Cloudflare

1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com).
2. Click **"Add a Site"**.
3. Enter: `lentisevent.gallery`
4. Select the **Free** plan (sufficient for Lentis).
5. Click **"Continue"**.

Cloudflare will scan for existing DNS records.

---

## Step 2: Update Nameservers at Your Registrar

Cloudflare will provide two nameservers. You must update these at your domain registrar.

1. Cloudflare will display something like:
   ```
  .ns1.cloudflare.com
   .ns2.cloudflare.com
   ```
   (These are examples — use the actual nameservers Cloudflare provides.)

2. Go to your domain registrar (where you purchased `lentisevent.gallery`).

3. Find the **nameserver** settings.

4. Replace the existing nameservers with the two Cloudflare nameservers.

5. Save the changes.

6. Wait for propagation. This can take **15 minutes to 48 hours**, but typically completes within a few hours.

**Do not proceed to Step 3 until nameserver changes have propagated.**

---

## Step 3: Create DNS Records

Once Cloudflare shows your domain as **"Active"** (nameservers propagated), create the required DNS records.

### Required Record

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| A | @ | 105.119.10.250 | Proxied (orange cloud) | Auto |

### Recommended Additional Records

| Type | Name | Content | Proxy | TTL |
|------|------|---------|-------|-----|
| CNAME | www | lentisevent.gallery | Proxied (orange cloud) | Auto |

**Important:** The `@` name represents the root domain (`lentisevent.gallery`).

The `www` CNAME ensures `www.lentisevent.gallery` also works.

### How to Create the Records

1. In Cloudflare Dashboard, go to **DNS** → **Records**.
2. Click **"Add record"**.
3. For the A record:
   - Type: `A`
   - Name: `@`
   - IPv4 address: `105.119.10.250`
   - Proxy status: **Proxied** (orange cloud icon)
   - TTL: Auto
4. Click **Save**.
5. Repeat for the www CNAME:
   - Type: `CNAME`
   - Name: `www`
   - Target: `lentisevent.gallery`
   - Proxy status: **Proxied**
   - TTL: Auto

---

## Step 4: Enable Cloudflare Proxy (Orange Cloud)

**This is critical for HTTPS.**

For each DNS record, ensure the proxy status shows an **orange cloud** icon.

- **Orange cloud (Proxied):** Cloudflare handles HTTPS, provides DDoS protection, CDN caching, and security features.
- **Grey cloud (DNS Only):** Cloudflare only resolves DNS. No HTTPS, no protection.

For Lentis Event Gallery, **all records should be proxied (orange cloud)**.

Why this matters:
- Cloudflare terminates TLS at its edge servers
- Your nginx only needs to listen on HTTP port 80
- Cloudflare provides free SSL/TLS certificates
- Cloudflare provides DDoS protection and CDN

---

## Step 5: Verify DNS Propagation

After creating the DNS records, verify they have propagated.

### Using nslookup

```bash
# Check root domain
nslookup lentisevent.gallery

# Check www subdomain
nslookup www.lentisevent.gallery
```

Expected output should show the Cloudflare IP addresses (not the origin server IP — Cloudflare proxies hide the origin).

### Using dig

```bash
dig lentisevent.gallery A +short
dig www.lentisevent.gallery CNAME +short
```

### Using curl

```bash
# Check if the domain resolves and responds
curl -I https://lentisevent.gallery

# Check the API health endpoint
curl https://lentisevent.gallery/api/health
```

**Do not proceed until DNS resolution works.**

---

## Step 6: Expected Live Endpoints

Once DNS is configured and the application is deployed, these endpoints should be accessible:

| Endpoint | Purpose |
|----------|---------|
| `https://lentisevent.gallery` | Main application (React SPA) |
| `https://lentisevent.gallery/api/health` | Backend health check |
| `https://lentisevent.gallery/api/health/ready` | Backend readiness check |
| `https://lentisevent.gallery/e/{slug}` | Public guest event page |
| `https://lentisevent.gallery/admin` | Admin dashboard |
| `https://lentisevent.gallery/host` | Host login/dashboard |

### Verification Commands

```bash
# Health
curl https://lentisevent.gallery/api/health
# Expected: {"status":"ok","app":"Lentis Gallery API","uptime_seconds":...}

# Readiness
curl https://lentisevent.gallery/api/health/ready
# Expected: {"status":"ok","dependencies":{"postgres":"connected","redis":"connected"}}

# Frontend
curl -I https://lentisevent.gallery/
# Expected: HTTP/2 200, Content-Type: text/html
```

---

## Troubleshooting

### DNS Not Resolving

- Wait longer (propagation can take up to 48 hours).
- Verify nameservers are correctly set at your registrar.
- Use https://dnschecker.org to check propagation status.

### Cloudflare Shows "Pending Nameserver Update"

- Nameserver changes haven't propagated yet.
- Wait and re-check.

### SSL/TLS Errors

- Ensure Cloudflare SSL/TLS mode is set to **"Full (strict)"** (see TLS setup guide).
- See `docs/TLS_AND_CLOUDFLARE_SETUP.md` for details.

### 502 Bad Gateway

- The origin server (your Docker stack) may not be running.
- Verify: `docker compose --env-file .env.production ps`
- Verify nginx is listening: `curl http://localhost/api/health`

---

## Cloudflare Plan Features

The **Free** plan includes:
- Unlimited bandwidth
- Free SSL/TLS certificates
- DDoS protection
- CDN caching
- Page Rules (3 free)
- Analytics

This is sufficient for Lentis Event Gallery.

---

## Next Steps

After DNS is configured:
1. Deploy the application: `docker compose --env-file .env.production up -d --build`
2. Configure Cloudflare SSL/TLS mode: see `docs/TLS_AND_CLOUDFLARE_SETUP.md`
3. Test all endpoints against the live domain
4. Test camera capture on mobile devices (requires HTTPS)
