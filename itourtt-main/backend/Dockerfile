# ── Build stage ──
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npx prisma generate
RUN NODE_OPTIONS="--max-old-space-size=3072" npm run build

# ── Production stage ──
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV TZ=Africa/Cairo

# Copy only what's needed for production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/generated ./generated
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/prisma.config.ts ./
COPY --from=builder /app/src/prisma/seed.ts ./src/prisma/seed.ts
COPY --from=builder /app/src/permissions/permission-registry.ts ./src/permissions/permission-registry.ts
COPY --from=builder /app/tsconfig.json ./

# Install system fonts so librsvg can render SVG text without squares
RUN apk add --no-cache font-dejavu fontconfig && fc-cache -f

# Create uploads directory and copy font assets
RUN mkdir -p /app/uploads
COPY --from=builder /app/fonts ./fonts

EXPOSE 3001

CMD ["node", "dist/src/main.js"]
