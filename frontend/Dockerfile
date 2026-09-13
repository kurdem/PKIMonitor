# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# ---- Serve stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
# Regenerate /config.js from env (PUBLIC_API_BASE, PUBLIC_API_KEY) at startup.
COPY docker-config-entrypoint.sh /docker-entrypoint.d/40-pkimonitor-config.sh
RUN chmod +x /docker-entrypoint.d/40-pkimonitor-config.sh
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
