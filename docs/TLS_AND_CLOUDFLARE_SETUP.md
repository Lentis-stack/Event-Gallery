# Lentis Gallery — TLS and Cloudflare Setup Guide

## Overview

Lentis Event Gallery requires HTTPS for:
- Camera capture (browser secure context requirement)
- Secure authentication cookies
- CORS security
- Production-grade security

The recommended approach is **Cloudflare as the TLS termination layer**.

---

## Recommended Architecture

```
Visitor (Browser)
    │ HTTPS
    ▼
Cloudflare Edge (TLS termination)
    │ HTTPS (Cloudflare Origin Certificate)
    ▼
Production Server
    │ HTTP (port 80)
    ▼
nginx (Docker)
    │
    ├── React SPA (static files)
    │
    └── /api/* → FastAPI Backend
                ├── PostgreSQL
                ├── Redis
                ├── Worker
                └── Cloudflare R2
```

**Why this architecture?**
- Cloudflare provides free TLS certificates
- Cloudflare provides DDoS protection
- Cloudflare provides a global CDN
- nginx only needs to listen on HTTP port 80
- Simpler operations — no certificate management needed on the server

---

## Why NOT Flexible SSL

Cloudflare offers three SSL modes:

| Mode | Description | Use for Lentis? |
|------|-------------|-----------------|
| **Off** | No encryption | ❌ Never |
| **Flexible** | Visitor→Cloudflare is HTTPS, Cloudflare→Server is HTTP | ❌ No |
| **Full** | Visitor→Cloudflare is HTTPS, Cloudflare→Server is HTTPS | ✅ Yes |
| **Full (Strict)** | As Full, but validates origin certificate | ✅ **Recommended** |

**Why Flexible SSL is inappropriate:**

1. **Security gap:** Traffic between Cloudflare and your server is unencrypted. Anyone on the network path can intercept data.

2. **Authentication bypass risk:** Session cookies may be transmitted over HTTP internally, allowing session hijacking.

3. **Mixed content:** The server doesn't know it's being accessed over HTTPS, so it may generate HTTP URLs that browsers block.

4. **Camera failures:** `navigator.mediaDevices.getUserMedia()` requires a secure context. If the page loads over HTTP internally, the camera may not work.

5. **Redirect loops:** Cloudflare→HTTP can cause redirect loops if the server tries to redirect HTTP→HTTPS.

**Always use Full or Full (strict) mode.**

---

## Step-by-Step Cloudflare SSL/TLS Configuration

### 1. Set SSL/TLS Mode to "Full (Strict)"

1. Log in to Cloudflare Dashboard
2. Select your domain: `lentisevent.gallery`
3. Go to **SSL/TLS** → **Overview**
4. Set the mode to **Full (strict)**

This tells Cloudflare:
- Encrypt traffic from visitor to Cloudflare (always)
- Encrypt traffic from Cloudflare to your server
- Validate that your server presents a valid SSL certificate

### 2. Enable "Always Use HTTPS"

1. Go to **SSL/TLS** → **Edge Certificates**
2. Enable **"Always Use HTTPS"**
3. This redirects all HTTP requests to HTTPS

### 3. Enable "Automatic HTTPS Rewrites"

1. In the same **Edge Certificates** section
2. Enable **"Automatic HTTPS Rewrites"**
3. This fixes mixed content issues automatically

### 4. Enable HSTS (Optional but Recommended)

1. Go to **SSL/TLS** → **Edge Certificates**
2. Scroll to **HTTP Strict Transport Security (HSTS)**
3. Click **Enable HSTS**
4. Set:
   - Max Age: `63072000` (2 years)
   - Include SubDomains: Yes
   - Preload: Yes (optional, submits to browser preload lists)
   - No-Sniff: Yes

**Warning:** HSTS is irreversible for the max-age period. Once enabled, browsers will refuse to connect via HTTP for the configured duration.

### 5. Configure Minimum TLS Version

1. Go to **SSL/TLS** → **Edge Certificates**
2. Set **Minimum TLS Version** to **TLS 1.2**

This prevents older, insecure TLS versions.

---

## Origin Server Certificate (Optional)

If you want Cloudflare to validate your server's certificate (required for **Full (strict)**), you need an origin certificate.

### Option A: Cloudflare Origin Certificate (Recommended)

1. Go to **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Select **"Generate private key and CSR with Cloudflare"**
4. Set validity: **15 years** (recommended)
5. Include: `lentisevent.gallery` and `*.lentisevent.gallery`
6. Click **Create**
7. Download the certificate and private key

**Installation on your server:**

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Save the certificate
sudo nano /etc/nginx/ssl/fullchain.pem
# Paste the certificate content

# Save the private key
sudo nano /etc/nginx/ssl/privkey.pem
# Paste the private key content

# Set permissions
sudo chmod 600 /etc/nginx/ssl/privkey.pem
sudo chmod 644 /etc/nginx/ssl/fullchain.pem
```

**Then update nginx.conf:**

1. Uncomment the HTTPS server block
2. Update the certificate paths
3. Rebuild: `docker compose --env-file .env.production up -d --build`

### Option B: Let's Encrypt (Alternative)

If you prefer Let's Encrypt certificates:

```bash
# Install certbot
sudo apt install certbot

# Obtain certificates
sudo certbot certonly --webroot -w /var/www/html \
    -d lentisevent.gallery \
    -d www.lentisevent.gallery

# Certificates are at:
# /etc/letsencrypt/live/lentisevent.gallery/fullchain.pem
# /etc/letsencrypt/live/lentisevent.gallery/privkey.pem
```

Then mount them into the Docker container and configure nginx.

---

## Certificate Security

**NEVER commit certificates or private keys to Git.**

Ensure `.gitignore` protects:

```
*.pem
*.key
*.cert
```

The `.gitignore` already includes these patterns.

For the Docker container, mount certificates as read-only volumes:

```yaml
frontend:
  volumes:
    - /etc/nginx/ssl/fullchain.pem:/etc/nginx/ssl/fullchain.pem:ro
    - /etc/nginx/ssl/privkey.pem:/etc/nginx/ssl/privkey.pem:ro
```

---

## Verification

### Test HTTPS Access

```bash
# Test root domain
curl -I https://lentisevent.gallery

# Test API health
curl https://lentisevent.gallery/api/health

# Test readiness
curl https://lentisevent.gallery/api/health/ready
```

### Test Security Headers

```bash
curl -I https://lentisevent.gallery 2>&1 | grep -i "strict-transport\|x-content-type\|x-frame\|content-security"
```

Expected headers:
```
strict-transport-security: max-age=63072000; includeSubDomains; preload
x-content-type-options: nosniff
x-frame-options: DENY
content-security-policy: default-src 'self'; ...
```

### Test Camera (Mobile Device)

1. Open `https://lentisevent.gallery/e/{event-slug}` on a mobile device
2. Tap "Take Photo"
3. Browser should request camera permission
4. Camera should activate

If the camera doesn't work, check:
- Is the URL HTTPS?
- Is the Cloudflare SSL mode set to Full?
- Does the browser show a lock icon?

---

## Troubleshooting

### "SSL_ERROR_RX_RECORD_TOO_LONG"

Cloudflare is connecting to your server on port 443 but your server is not listening on 443.

**Fix:** Set Cloudflare SSL mode to "Flexible" temporarily, or configure nginx to listen on 443.

### "ERR_TOO_MANY_REDIRECTS"

Cloudflare is in "Flexible" mode but your server redirects HTTP→HTTPS, creating a loop.

**Fix:** Set Cloudflare SSL mode to "Full" or "Full (strict)".

### "ERR_SSL_VERSION_OR_CIPHER_MISMATCH"

Your server's TLS configuration is too old.

**Fix:** Ensure nginx is configured with TLS 1.2+ (see nginx.conf HTTPS block).

### Mixed Content Warnings

The page loads over HTTPS but some resources load over HTTP.

**Fix:** Enable Cloudflare's "Automatic HTTPS Rewrites" and ensure `VITE_PUBLIC_URL` uses `https://`.

### Camera Not Working

- Verify the URL starts with `https://`
- Check browser console for security errors
- Verify `VITE_PUBLIC_URL` is set to `https://lentisevent.gallery`
- Test on a real mobile device (not just localhost)

---

## Configuration Checklist

| Setting | Value | Location |
|---------|-------|----------|
| Cloudflare SSL mode | Full (strict) | Cloudflare Dashboard → SSL/TLS |
| Always Use HTTPS | Enabled | Cloudflare Dashboard → SSL/TLS → Edge Certificates |
| Automatic HTTPS Rewrites | Enabled | Cloudflare Dashboard → SSL/TLS → Edge Certificates |
| Minimum TLS Version | TLS 1.2 | Cloudflare Dashboard → SSL/TLS → Edge Certificates |
| HSTS | Enabled (optional) | Cloudflare Dashboard → SSL/TLS → Edge Certificates |
| FRONTEND_URL | `https://lentisevent.gallery` | `.env.production` |
| VITE_PUBLIC_URL | `https://lentisevent.gallery` | `.env.production` |
| nginx HSTS header | Uncommented (when ready) | `nginx.conf` |
