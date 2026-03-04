# ── Stage 1: Install deps ─────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY app/frontend/package.json app/frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps

# ── Stage 2: Build ────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY app/frontend/ .
# In Docker, frontend talks to backend via internal Docker network
ENV NEXT_PUBLIC_API_BASE_URL=""
ENV NODE_ENV=production
RUN npm run build

# ── Stage 3: Run (standalone output) ─────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
