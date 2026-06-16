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
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV LISTEN_HOST=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./apps/web/.next/static
COPY --from=builder /app/public ./apps/web/public
EXPOSE 3000
CMD ["sh", "-c", "HOSTNAME=\"${LISTEN_HOST:-0.0.0.0}\" PORT=\"${PORT:-3000}\" node apps/web/server.js"]
