# ── Stage 1: Build ──
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npx vite build

# ── Stage 2: Serve with nginx ──
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# SPA fallback for client routes + reverse proxy /api/ → backend:8000.
# Without the proxy, POSTs to /api/* hit `try_files` and nginx returns 405.
RUN printf 'server {\n\
  listen 80;\n\
  server_name _;\n\
  root /usr/share/nginx/html;\n\
  index index.html;\n\
  client_max_body_size 50m;\n\
  types {\n\
    text/javascript js mjs;\n\
    text/css css;\n\
    text/html html htm;\n\
    image/png png;\n\
    image/jpeg jpg jpeg;\n\
    image/svg+xml svg;\n\
    image/webp webp;\n\
    image/x-icon ico;\n\
    application/json json map;\n\
    application/wasm wasm;\n\
    font/woff woff;\n\
    font/woff2 woff2;\n\
  }\n\
  location /api/ {\n\
    proxy_pass http://backend:8000;\n\
    proxy_http_version 1.1;\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
    proxy_set_header X-Forwarded-Proto $scheme;\n\
    proxy_read_timeout 180s;\n\
    proxy_send_timeout 180s;\n\
    proxy_connect_timeout 30s;\n\
  }\n\
  location / {\n\
    try_files $uri $uri/ /index.html;\n\
  }\n\
  location /health {\n\
    return 200 "ok";\n\
    add_header Content-Type text/plain;\n\
  }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1
