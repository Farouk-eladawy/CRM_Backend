# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 3.1.x   | Yes                |
| < 3.0   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in iTourTT, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please send an email to:

- **Email**: mggouda@gmail.com
- **Subject**: `[SECURITY] iTourTT - Brief description`

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Resolution**: Depending on severity, critical issues will be prioritized

### What to expect

- You will receive confirmation that your report was received
- We will investigate and validate the vulnerability
- We will work on a fix and coordinate disclosure
- Credit will be given to reporters unless anonymity is requested

## Security Best Practices

This project implements:

- JWT authentication with refresh token rotation
- Role-based access control (RBAC) with granular permissions
- Input validation on all API endpoints
- Parameterized queries via Prisma ORM (SQL injection prevention)
- Audit logging on all mutating operations
- Financial records are immutable after posting
