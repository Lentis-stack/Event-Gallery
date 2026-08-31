#!/bin/sh
# ============================================================
# Lentis Gallery — Frontend Runtime Entrypoint
# ============================================================
# Vite embeds env vars at BUILD time. For runtime configurability
# (e.g., different VITE_PUBLIC_URL per deployment), we inject
# values into the built JS bundle before starting nginx.
#
# This replaces the placeholder "__VITE_PUBLIC_URL__" in the
# built assets with the actual runtime value.
# ============================================================

set -e

# Inject VITE_PUBLIC_URL if set
if [ -n "$VITE_PUBLIC_URL" ]; then
    # Find the main JS bundle and replace the placeholder
    # The placeholder is set in src/services/config.ts as a fallback
    find /usr/share/nginx/html/assets -name "*.js" -exec \
        sed -i "s|__VITE_PUBLIC_URL__|${VITE_PUBLIC_URL}|g" {} +
    echo "[entrypoint] Injected VITE_PUBLIC_URL=${VITE_PUBLIC_URL}"
else
    echo "[entrypoint] VITE_PUBLIC_URL not set, using build-time default"
fi

# Execute the main command (nginx)
exec "$@"
