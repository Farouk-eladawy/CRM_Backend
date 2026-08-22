import {
  Injectable,
  BadRequestException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createHmac } from 'node:crypto';
import type {
  PaymentGateway,
  PaymentSessionResult,
  PaymentVerificationResult,
  PaymentCustomer,
} from './gateway.interface.js';

/**
 * Shape of the callback payload that GetPayIn (Paylink) sends both via the
 * server-to-server webhook (POST body) and the browser redirect (query string).
 * `message` is optional on the redirect.
 */
export interface GetPayInCallback {
  success: boolean | string;
  invoice_id: number | string;
  invoice_status: string; // PAID | UNPAID
  message?: string;
  signature: string;
}

/**
 * GetPayIn (Paylink) hosted-checkout gateway.
 *
 * Flow: POST /api/integration/init (signed) → returns a hosted `checkout_url`
 * we redirect the guest to. GetPayIn then notifies us of the result twice:
 *   1. a server-to-server webhook (source of truth → marks the booking paid)
 *   2. a browser redirect back to our configured Redirect URL
 * Both carry an HMAC signature verified with the secret Hash Token.
 *
 * Webhook URL and Redirect URL are configured once in the GetPayIn dashboard
 * (not passed per-request), so `returnUrl`/`cancelUrl` here are ignored.
 */
@Injectable()
export class GetPayInGateway implements PaymentGateway {
  private readonly logger = new Logger(GetPayInGateway.name);

  constructor(private readonly configService: ConfigService) {}

  private get baseUrl(): string {
    return (
      this.configService.get<string>('GETPAYIN_BASE_URL') ||
      'https://pay.getpayin.com'
    ).replace(/\/+$/, '');
  }

  private getCredentials(): { authToken: string; hashToken: string } {
    const authToken = this.configService.get<string>('GETPAYIN_AUTH_TOKEN');
    const hashToken = this.configService.get<string>('GETPAYIN_HASH_TOKEN');
    if (!authToken || !hashToken) {
      throw new BadRequestException(
        'GetPayIn is not configured. Set GETPAYIN_AUTH_TOKEN and GETPAYIN_HASH_TOKEN.',
      );
    }
    return { authToken, hashToken };
  }

  /** base64( HMAC-SHA256( payload, hashToken ) ) — the init request signature. */
  private signBase64(payload: string, hashToken: string): string {
    return createHmac('sha256', hashToken).update(payload, 'utf8').digest('base64');
  }

  /** hex( HMAC-SHA256( payload, hashToken ) ) — used by some callback formats. */
  private signHex(payload: string, hashToken: string): string {
    return createHmac('sha256', hashToken).update(payload, 'utf8').digest('hex');
  }

  async createSession(
    bookingRef: string,
    amount: number,
    currency: string,
    _returnUrl: string,
    _cancelUrl: string,
    customer?: PaymentCustomer,
  ): Promise<PaymentSessionResult> {
    const { authToken, hashToken } = this.getCredentials();

    // Exact string sent must equal the string we sign — never derive twice.
    const firstName = customer?.firstName?.trim() || 'Guest';
    const lastName = customer?.lastName?.trim() || bookingRef;
    const email = customer?.email?.trim() || '';
    const orderTitle = customer?.orderTitle?.trim() || `Booking ${bookingRef}`;
    const orderAmount = String(amount);
    const address = customer?.address?.trim() || '';
    const city = customer?.city?.trim() || '';
    const country = customer?.country?.trim() || '';
    const cur = currency.toUpperCase();

    // Signature: concatenate field values in the documented order (token and
    // signature excluded; optional fields included even when empty).
    const concatenated =
      firstName + lastName + email + orderTitle + orderAmount + address + city + country + cur;
    const signature = this.signBase64(concatenated, hashToken);

    const form = new FormData();
    form.append('token', authToken);
    form.append('first_name', firstName);
    form.append('last_name', lastName);
    form.append('email', email);
    form.append('order_title', orderTitle);
    form.append('order_amount', orderAmount);
    form.append('address', address);
    form.append('city', city);
    form.append('country', country);
    form.append('currency', cur);
    form.append('signature', signature);

    // Optional checkout line items. Excluded from the signature by the API, so
    // it can be appended freely. Drop empty-value rows and cap at the documented
    // 2000-char limit (omit entirely if that would truncate mid-JSON).
    const rows = (customer?.orderDetails ?? []).filter(
      (r) => r.label?.trim() && r.value?.trim(),
    );
    if (rows.length > 0) {
      const encoded = JSON.stringify(
        rows.map((r) => ({ label: r.label.trim(), value: r.value.trim() })),
      );
      if (encoded.length <= 2000) {
        form.append('order_details', encoded);
      } else {
        this.logger.warn(
          `GetPayIn order_details for booking ${bookingRef} exceeds 2000 chars; omitting.`,
        );
      }
    }

    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}/api/integration/init`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: form,
      });
    } catch (err) {
      this.logger.error(`GetPayIn init request failed: ${(err as Error).message}`);
      throw new BadRequestException('Could not reach the payment gateway.');
    }

    const json = (await res.json().catch(() => ({}))) as {
      success?: boolean;
      message?: string;
      data?: { checkout_url?: string; invoice_id?: number | string; expires_at?: string };
    };

    if (!res.ok || !json?.success || !json.data?.checkout_url) {
      this.logger.error(
        `GetPayIn init rejected (HTTP ${res.status}): ${json?.message ?? 'unknown error'}`,
      );
      throw new BadRequestException(
        json?.message || 'Payment gateway rejected the request.',
      );
    }

    return {
      sessionId: String(json.data.invoice_id ?? ''),
      checkoutUrl: json.data.checkout_url,
      gateway: 'GETPAYIN',
    };
  }

  /**
   * Verify a callback (webhook or redirect) signature. GetPayIn signs the
   * concatenation of `success + invoice_id + invoice_status + message`, but the
   * exact rendering of the boolean/int and the digest encoding aren't pinned
   * down in the docs — so we accept any of the plausible renderings. This is
   * still secure: every candidate requires the secret Hash Token.
   */
  verifyCallback(payload: GetPayInCallback): boolean {
    const { hashToken } = this.getCredentials();
    const received = (payload.signature || '').trim();
    if (!received) return false;

    const invoiceId = String(payload.invoice_id ?? '');
    const status = String(payload.invoice_status ?? '');
    const message = payload.message ?? '';
    const successRenders = [
      String(payload.success), // "true" / "false"
      payload.success === true || payload.success === 'true' ? '1' : '0',
    ];

    const candidates: string[] = [];
    for (const s of successRenders) {
      const base = s + invoiceId + status + message;
      const baseNoMsg = s + invoiceId + status;
      for (const c of [base, baseNoMsg]) {
        candidates.push(this.signBase64(c, hashToken));
        candidates.push(this.signHex(c, hashToken));
      }
    }

    const ok = candidates.some(
      (c) => c.toLowerCase() === received.toLowerCase(),
    );
    if (!ok) {
      this.logger.warn(
        `GetPayIn callback signature mismatch for invoice ${invoiceId}. ` +
          `Received="${received}". Tried ${candidates.length} renderings.`,
      );
    }
    return ok;
  }

  async verifyPayment(_sessionId: string): Promise<PaymentVerificationResult> {
    // GetPayIn is push-based (webhook/redirect); there is no documented pull
    // status endpoint, so we rely on the signed callbacks instead.
    throw new BadRequestException(
      'GetPayIn does not expose a status-pull endpoint; rely on webhook/redirect callbacks.',
    );
  }

  async refund(
    _transactionId: string,
    _amount: number,
  ): Promise<{ success: boolean; refundId: string }> {
    throw new BadRequestException(
      'GetPayIn refunds are not available via the integration API. Refund from the GetPayIn dashboard.',
    );
  }
}
