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
# 认证总开关（build-time）：默认 false（测试期直接进入系统）
ARG NEXT_PUBLIC_AUTH_ENABLED=false
ENV NEXT_PUBLIC_AUTH_ENABLED=${NEXT_PUBLIC_AUTH_ENABLED}
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# 前端容器监听端口，默认 80（nginx 惯例）
ENV PORT=80
ENV LISTEN_HOST=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./apps/web/.next/static
COPY --from=builder /app/public ./apps/web/public
EXPOSE 80
CMD ["sh", "-c", "HOSTNAME=\"${LISTEN_HOST:-0.0.0.0}\" PORT=\"${PORT:-80}\" node apps/web/server.js"]
