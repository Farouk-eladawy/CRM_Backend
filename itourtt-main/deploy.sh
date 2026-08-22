#!/bin/bash
set -e

USAGE="Usage: $0 [production]"
ENV="${1:-production}"

if [[ "$ENV" != "production" ]]; then
  echo "$USAGE"
  exit 1
fi

cd /opt/itour

# ── Pull latest code from GitHub ──
echo ""
echo ">> Pulling latest code from GitHub (main)..."
git pull origin main

# ── Derive version from package.json ──
VERSION=$(node -p "require('./backend/package.json').version")
echo ">> Version: $VERSION"

# ── Build shared backend image (same for all environments) ──
echo ""
echo ">> Building backend image..."
docker build --no-cache -t itourtt-backend:${VERSION} backend -q

# ── Build frontend image (Production: Car Dispatch enabled) ──
echo ">> Building frontend image (with Car Dispatch)..."
docker build --no-cache \
  --build-arg NEXT_PUBLIC_ENABLE_CAR_DISPATCH=true \
  -t itourtt-frontend:${VERSION}-cardispatch frontend -q
docker save itourtt-frontend:${VERSION}-cardispatch | k3s ctr images import -

# Import backend image into k3s
echo ">> Importing backend image into k3s..."
docker save itourtt-backend:${VERSION} | k3s ctr images import -

deploy_env() {
  local ns="$1"
  local label="$2"
  local frontend_tag="$3"

  echo ""
  echo "=== Deploying $label ($ns) ==="

  # Point both deployments to the new image tags
  kubectl set image deployment/backend backend=itourtt-backend:${VERSION} -n "$ns"
  kubectl set image deployment/frontend frontend=itourtt-frontend:${frontend_tag} -n "$ns"

  # Scale to 2 replicas
  echo ">> Scaling to 2 replicas..."
  kubectl scale deployment/backend --replicas=2 -n "$ns" 2>&1 || true
  kubectl scale deployment/frontend --replicas=2 -n "$ns" 2>&1 || true

  # Rollout backend FIRST so migration runs from the NEW image
  echo ">> Rolling out backend..."
  kubectl rollout restart deployment/backend -n "$ns"
  kubectl rollout status deployment/backend -n "$ns" --timeout=120s

  # Run migrations AFTER rollout — new image has the new migration files
  echo ">> Running database migrations..."
  kubectl exec -n "$ns" deployment/backend -- npx prisma migrate deploy 2>&1 || true

  # Sync schema (catch any drift not covered by migrations)
  echo ">> Syncing database schema..."
  kubectl exec -n "$ns" deployment/backend -- npx prisma db push --accept-data-loss 2>&1 || true

  # Run seed AFTER migration
  echo ">> Running database seed (permissions + system params skipped)..."
  kubectl exec -n "$ns" deployment/backend -- env SKIP_PERMISSION_SEED=true SKIP_SYSTEM_PARAMS_SEED=true node dist/src/prisma/seed.js 2>&1 || true

  # Restart frontend
  echo ">> Rolling out frontend..."
  kubectl rollout restart deployment/frontend -n "$ns"
  kubectl rollout status deployment/frontend -n "$ns" --timeout=120s

  echo ">> $label deployed successfully!"
}

deploy_env "itour-production" "Production" "${VERSION}-cardispatch"

# ── Cleanup: aggressively remove old images to save disk space ──
echo ""
echo ">> Cleaning up Docker images and build cache..."

# Remove all unused Docker images (not just dangling — full prune)
docker image prune -af -q 2>/dev/null || true

# Remove old versioned itourtt images from Docker (keep only current VERSION)
docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" \
  | grep -E "^itourtt-(backend|frontend):" \
  | grep -v ":${VERSION}" \
  | awk '{print $2}' \
  | xargs -r docker rmi -f 2>/dev/null || true

# Remove all Docker build cache
docker builder prune -af -q 2>/dev/null || true

# Remove unused containerd/k3s images (untagged digests not referenced by any pod)
echo ">> Cleaning up k3s containerd images..."
RUNNING_IMAGES=$(kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{range .spec.containers[*]}{.image}{"\n"}{end}{end}' 2>/dev/null | sort -u)
k3s ctr images ls -q 2>/dev/null | while read img; do
  if ! echo "$RUNNING_IMAGES" | grep -qF "$img"; then
    k3s ctr images rm "$img" 2>/dev/null || true
  fi
done

# Show disk usage after cleanup
echo ">> Disk usage after cleanup:"
df -h / | awk 'NR==2 {printf "   %s used of %s (%s free)\n", $3, $2, $4}'

echo ""
echo "=== Deployment complete ==="
echo "Production:  https://fulvago.itourtt.cloud"
df -h / | awk 'NR==2 {printf "Disk:        %s used of %s (%s)\n", $3, $2, $5}'
