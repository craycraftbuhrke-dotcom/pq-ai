FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# 生产镜像必须显式启用认证。
ARG NEXT_PUBLIC_AUTH_ENABLED
ENV NEXT_PUBLIC_AUTH_ENABLED=${NEXT_PUBLIC_AUTH_ENABLED}
ARG NEXT_PUBLIC_ALLOW_SELF_REGISTRATION=false
ENV NEXT_PUBLIC_ALLOW_SELF_REGISTRATION=${NEXT_PUBLIC_ALLOW_SELF_REGISTRATION}
RUN test "${NEXT_PUBLIC_AUTH_ENABLED}" = "true" && npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV AUTH_ENABLED=true
# 前端容器监听端口，默认 80（nginx 惯例）
ENV PORT=80
ENV LISTEN_HOST=0.0.0.0
COPY --chown=node:node --from=builder /app/.next/standalone ./
COPY --chown=node:node --from=builder /app/.next/static ./.next/static
COPY --chown=node:node --from=builder /app/public ./public
ENV WEB_PUBLIC_DIR=/app/public
USER node
EXPOSE 80
CMD ["sh", "-c", ": \"${AUTH_ENABLED:?AUTH_ENABLED must be true}\"; [ \"$AUTH_ENABLED\" = \"true\" ] || exit 1; HOSTNAME=\"${LISTEN_HOST:-0.0.0.0}\" PORT=\"${PORT:-80}\" node server.js"]
