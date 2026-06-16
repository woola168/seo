FROM node:24-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
COPY apps/admin-portal/package.json ./apps/admin-portal/package.json

RUN npm ci

COPY apps/admin-portal ./apps/admin-portal

RUN npm run build:portal

FROM nginx:1.29-alpine

COPY apps/admin-portal/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/admin-portal/dist /usr/share/nginx/html

EXPOSE 80
