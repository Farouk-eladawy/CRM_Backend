// MG License Server client — HMAC secret DELETED (was forgeable).
// This app now holds only the PUBLIC key and verifies Ed25519 tokens; it cannot forge.
// Crypto + network live in ./license-verify.ts. This file only keeps the response SHAPE
// the frontend depends on and maps the verifier's CheckResult onto it.
import type { CheckResult, LicenseStatus as VerifyStatus } from './license-verify.js';

export interface LicenseStatus {
  valid: boolean;
  expiresAt: string | null; // YYYY-MM-DD (unchanged shape)
  daysRemaining: number | null;
  message: string;
  status: VerifyStatus;      // raw verdict: active | grace | expired | revoked | invalid | domain_mismatch | install_blocked | ip_mismatch | grace_expired
  checkedOnline: boolean;    // was this verdict confirmed against the license server this call?
  lastCheckedAt: string | null; // ISO of the last successful ONLINE check (from DB); filled by the service
}

const MESSAGES: Record<VerifyStatus, string> = {
  active: 'License active',
  grace: 'License valid — renew soon',
  expired: 'License has expired',
  revoked: 'License has been revoked',
  invalid: 'Invalid license key',
  domain_mismatch: 'License not valid for this host',
  install_blocked: 'Install limit reached for this license',
  ip_mismatch: 'License not valid for this server',
  grace_expired: 'Unable to verify license — contact support',
};

/** Map the verifier's CheckResult onto the LicenseStatus shape (now carries the raw verdict too). */
export function toLicenseStatus(r: CheckResult, lastCheckedAt: string | null = null): LicenseStatus {
  const expiresAt = r.expiresAt ? r.expiresAt.slice(0, 10) : null; // ISO → YYYY-MM-DD
  const daysRemaining =
    r.daysRemaining ??
    (r.expiresAt ? Math.ceil((Date.parse(r.expiresAt) - Date.now()) / 86_400_000) : null);
  return {
    valid: r.ok,
    expiresAt,
    daysRemaining,
    message: MESSAGES[r.status],
    status: r.status,
    checkedOnline: r.checkedOnline,
    lastCheckedAt,
  };
}

/**
 * Accept the public key in either raw PEM (with real or `\n`-escaped newlines) or a
 * base64-wrapped PEM blob (how the license server stores it). Returns clean PEM.
 */
export function normalizePublicKey(raw: string | undefined): string {
  const v = (raw ?? '').trim();
  if (v.startsWith('-----')) return v.replace(/\\n/g, '\n');
  return Buffer.from(v, 'base64').toString('utf8');
}
