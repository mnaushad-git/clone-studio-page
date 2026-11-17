# Production image for the storefront and Admin Portal: TanStack Start SSR on plain Node.
# No Lovable or Cloudflare service is involved at build time or at runtime.
#
# Build from the repository root. VITE_* values are compiled into the browser bundle, so
# each environment needs its own image:
#   docker build -f deploy/frontend.Dockerfile \
#     --build-arg VITE_API_BASE_URL=https://api.terrific-bites.trunexus.ai \
#     --build-arg VITE_DEMO_MODE=true \
#     -t terrific-bites-frontend:<git-sha> .
FROM node:22-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL
ARG VITE_DEMO_MODE=true
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_DEMO_MODE=$VITE_DEMO_MODE

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN test -n "$VITE_API_BASE_URL" && npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

# Nitro's node-server output is self-contained: no node_modules needed at runtime.
COPY --from=build --chown=node:node /app/.output ./.output
USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.status<500?0:1)).catch(()=>process.exit(1))"

CMD ["node", ".output/server/index.mjs"]
