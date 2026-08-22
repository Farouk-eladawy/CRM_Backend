import { Injectable, BadRequestException, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

/**
 * Cloudflare Turnstile verification — bot/abuse protection for unauthenticated
 * write endpoints (e.g. guest booking creation).
 *
 * Activation is OPT-IN: if `TURNSTILE_SECRET` is not configured the service is
 * a no-op, so existing flows keep working until the frontend widget + secret
 * are wired up. Once the secret is set, a valid token becomes mandatory.
 */
@Injectable()
export class CaptchaService {
  private readonly logger = new Logger(CaptchaService.name);
  private readonly secret?: string;

  constructor(private readonly config: ConfigService) {
    this.secret = this.config.get<string>('TURNSTILE_SECRET') || undefined;
  }

  get enabled(): boolean {
    return !!this.secret;
  }

  /**
   * Throws BadRequestException if verification is enabled and the token is
   * missing/invalid. Silently passes when disabled.
   */
  async assertValid(token: string | undefined, remoteIp?: string): Promise<void> {
    if (!this.secret) return; // disabled — no-op

    if (!token) {
      throw new BadRequestException('Captcha verification is required.');
    }

    try {
      const body = new URLSearchParams();
      body.append('secret', this.secret);
      body.append('response', token);
      if (remoteIp) body.append('remoteip', remoteIp);

      const res = await fetch(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        { method: 'POST', body },
      );
      const data = (await res.json()) as { success: boolean };

      if (!data.success) {
        throw new BadRequestException('Captcha verification failed.');
      }
    } catch (err) {
      if (err instanceof BadRequestException) throw err;
      // Network/parse error — fail closed (the endpoint is security-sensitive).
      this.logger.error(`Turnstile verification error: ${(err as Error).message}`);
      throw new BadRequestException('Captcha verification could not be completed.');
    }
  }
}
