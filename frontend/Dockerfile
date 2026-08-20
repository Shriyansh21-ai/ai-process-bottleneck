# Multi-stage build for the Agent Operations Dashboard.
# Stage 1 builds the static SPA; stage 2 serves it with nginx.
#
# VITE_API_URL is baked at BUILD time (Vite inlines import.meta.env). It must be
# the URL the *browser* uses to reach the backend — for the local compose stack
# that is the host-exposed backend port (http://localhost:8000), NOT the compose
# service name (which only resolves inside the network).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine AS serve
# SPA-aware nginx config (deep-link fallback to index.html).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
