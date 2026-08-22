import { SetMetadata } from '@nestjs/common';

/**
 * Marks a route (or whole controller) as publicly accessible, bypassing the
 * globally-registered JwtAuthGuard. Use sparingly — only for endpoints that
 * are genuinely meant to be reached without authentication (login, public B2C
 * API, payment webhooks, health check).
 */
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
