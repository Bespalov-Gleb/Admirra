# Build stage
FROM node:20-alpine as build-stage

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG VITE_ADMIRRA_DEPLOY_ENV=prod
ARG VITE_ADMIRRA_PUBLIC_HOST=
ENV VITE_ADMIRRA_DEPLOY_ENV=$VITE_ADMIRRA_DEPLOY_ENV
ENV VITE_ADMIRRA_PUBLIC_HOST=$VITE_ADMIRRA_PUBLIC_HOST

RUN npm run build

# Production stage
FROM nginx:stable-alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
