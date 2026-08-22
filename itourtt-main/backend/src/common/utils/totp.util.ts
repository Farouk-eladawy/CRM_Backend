import * as crypto from 'crypto';

/**
 * TOTP (RFC 6238) + HOTP (RFC 4226) + base32 (RFC 4648) using only Node stdlib.
 * No external dependency.
 *
 * Used for optional user 2FA. Compatible with Google Authenticator / Authy / 1Password.
 */

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';

export function base32Encode(buf: Buffer): string {
  let bits = 0;
  let value = 0;
  let out = '';
  for (const byte of buf) {
    value = (value << 8) | byte;
    bits += 8;
    while (bits >= 5) {
      out += BASE32_ALPHABET[(value >>> (bits - 5)) & 31];
      bits -= 5;
    }
  }
  if (bits > 0) out += BASE32_ALPHABET[(value << (5 - bits)) & 31];
  return out;
}

export function base32Decode(input: string): Buffer {
  const clean = input.replace(/=+$/, '').toUpperCase().replace(/\s/g, '');
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const char of clean) {
    const idx = BASE32_ALPHABET.indexOf(char);
    if (idx === -1) continue;
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

/** Random base32 secret (default 20 bytes → 160 bits, per RFC 6238 recommendation). */
export function generateTotpSecret(bytes = 20): string {
  return base32Encode(crypto.randomBytes(bytes));
}

/** HOTP for a given 8-byte counter. */
function hotp(secret: Buffer, counter: number, digits = 6): string {
  const buf = Buffer.alloc(8);
  // JS bitwise is 32-bit; write counter as big-endian across both halves.
  buf.writeUInt32BE(Math.floor(counter / 0x100000000), 0);
  buf.writeUInt32BE(counter >>> 0, 4);
  const hmac = crypto.createHmac('sha1', secret).update(buf).digest();
  const offset = hmac[hmac.length - 1] & 0xf;
  const code =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);
  return (code % 10 ** digits).toString().padStart(digits, '0');
}

/** Current TOTP code. */
export function generateTotp(
  secretBase32: string,
  atMs = Date.now(),
  stepSeconds = 30,
  digits = 6,
): string {
  const counter = Math.floor(atMs / 1000 / stepSeconds);
  return hotp(base32Decode(secretBase32), counter, digits);
}

/**
 * Verify a submitted code, tolerating ±`window` steps of clock drift
 * (window=1 → accepts the previous, current, and next 30s code).
 * Constant-time compare per candidate.
 */
export function verifyTotp(
  secretBase32: string,
  token: string,
  window = 1,
  atMs = Date.now(),
  stepSeconds = 30,
  digits = 6,
): boolean {
  const clean = (token || '').replace(/\s/g, '');
  if (clean.length !== digits) return false;
  const secret = base32Decode(secretBase32);
  const base = Math.floor(atMs / 1000 / stepSeconds);
  for (let i = -window; i <= window; i++) {
    const candidate = hotp(secret, base + i, digits);
    if (
      candidate.length === clean.length &&
      crypto.timingSafeEqual(Buffer.from(candidate), Buffer.from(clean))
    ) {
      return true;
    }
  }
  return false;
}

/** otpauth:// URI for QR provisioning in an authenticator app. */
export function otpauthUri(
  secretBase32: string,
  accountLabel: string,
  issuer = 'iTourTT',
): string {
  const label = encodeURIComponent(`${issuer}:${accountLabel}`);
  const params = new URLSearchParams({
    secret: secretBase32,
    issuer,
    algorithm: 'SHA1',
    digits: '6',
    period: '30',
  });
  return `otpauth://totp/${label}?${params.toString()}`;
}

/** One-time recovery codes (for lost-authenticator fallback). Store hashed. */
export function generateRecoveryCodes(count = 10): string[] {
  return Array.from({ length: count }, () =>
    crypto.randomBytes(5).toString('hex').replace(/(.{5})(.{5})/, '$1-$2'),
  );
}
