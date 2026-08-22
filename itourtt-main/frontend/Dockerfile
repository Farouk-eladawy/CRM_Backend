# ── Build stage ──
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# NOTE: Do NOT pass NEXT_PUBLIC_API_URL — the axios client already appends /api
# and the ingress routes /api/* to the backend. Passing it would double the prefix.

# Feature flag: Car Dispatch (baked into client bundle at build time)
ARG NEXT_PUBLIC_ENABLE_CAR_DISPATCH
ENV NEXT_PUBLIC_ENABLE_CAR_DISPATCH=${NEXT_PUBLIC_ENABLE_CAR_DISPATCH}

# Bake version from package.json into the client bundle
ENV NEXT_PUBLIC_APP_VERSION=${NEXT_PUBLIC_APP_VERSION}
RUN export NEXT_PUBLIC_APP_VERSION=$(node -p "require('./package.json').version") && NODE_OPTIONS="--max-old-space-size=4096" npm run build

# ── Production stage ──
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy standalone Next.js output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
