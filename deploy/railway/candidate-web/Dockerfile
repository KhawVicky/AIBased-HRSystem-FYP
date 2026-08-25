FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY styles ./styles
COPY public ./public
COPY index.html tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts ./

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_SURFACE=candidate

RUN test -n "$VITE_API_BASE_URL" && npm run build

FROM nginx:1.27-alpine

COPY deploy/railway/candidate-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
