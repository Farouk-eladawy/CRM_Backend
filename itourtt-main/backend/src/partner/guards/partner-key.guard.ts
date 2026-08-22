import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import * as crypto from 'crypto';

/**
 * Machine-to-machine auth for the /api/partner/* seam (B2C standalone → iTourTT).
 * Validates the `X-Partner-Key` header against PARTNER_API_KEY (timing-safe).
 * Fails closed: if PARTNER_API_KEY is unset, every partner request is denied.
 */
@Injectable()
export class PartnerKeyGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest();
    const provided: string = req.headers['x-partner-key'] ?? '';
    const expected = process.env.PARTNER_API_KEY ?? '';

    if (!expected) {
      throw new UnauthorizedException('Partner API not configured');
    }
    const a = Buffer.from(provided);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
      throw new UnauthorizedException('Invalid partner key');
    }
    return true;
  }
}
