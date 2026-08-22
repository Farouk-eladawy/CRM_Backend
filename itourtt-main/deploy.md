# Production Deployment

The VPS runs **k3s** with one active namespace:

| Namespace | URL | Car Dispatch |
|---|---|---|
| `itour-production` | https://fulvago.itourtt.cloud | enabled |

## Deploy

```bash
cd /opt/itour

# Deploy production (pulls from GitHub first)
./deploy.sh production
```

The script will:
1. `git pull origin main` — fetch latest code from GitHub
2. Build Docker images locally (backend + frontend variants)
3. Import images into k3s (`k3s ctr images import`)
4. Roll out backend → run `prisma migrate deploy` + `prisma db push` + seed
5. Roll out frontend
6. Scale each deployment to 2 replicas

## Image tags

| Image | Tag |
|---|---|
| `itourtt-backend` | `3.3.12` |
| `itourtt-frontend` (production) | `3.3.12-cardispatch` |
