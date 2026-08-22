# Contributing to iTourTT

Thank you for your interest in contributing to iTourTT. This is a proprietary project, so contributions are managed through a controlled process.

## Getting Started

1. Contact the project maintainer at **mggouda@gmail.com** to discuss your proposed contribution
2. Obtain a valid license agreement before accessing the codebase
3. Fork the repository and create a feature branch from `main`

## Development Setup

### Prerequisites

- Node.js 20+
- PostgreSQL 16+
- npm

### Local Development

```bash
# Backend
cd backend
npm install
npx prisma generate
npm run start:dev

# Frontend
cd frontend
npm install
npm run dev
```

## Branch Naming

- `feat/description` — new features
- `fix/description` — bug fixes
- `docs/description` — documentation updates

## Commit Messages

Follow conventional commit format:

```
feat: add new dispatch feature
fix: resolve login redirect issue
docs: update API documentation
```

## Pull Request Process

1. Ensure your code compiles without errors (`npx tsc --noEmit`)
2. Update documentation if you changed any public API
3. Fill out the pull request template completely
4. Request review from the project maintainer

## Code Standards

- TypeScript strict mode
- REST API conventions
- Prisma ORM for all database operations
- No business logic in the database layer
- Audit logging on all create/update/delete operations

## Reporting Issues

Use GitHub Issues with the provided templates for:

- Bug reports
- Feature requests

## Contact

- **Mohamed Gouda** — mggouda@gmail.com
