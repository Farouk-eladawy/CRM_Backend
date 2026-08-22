/**
 * MG License client verifier — reference implementation.
 *
 * Drop this one file into a client app. Zero dependencies (Node `crypto` + global `fetch`).
 * Framework-agnostic: call `checkLicense()` from a NestJS guard, a Next.js middleware, a
 * cron job — anywhere. The caller owns persistence of `token`, `installId`, `lastGoodCheck`.
 *
 * Hybrid model:
 *   - OFFLINE (every call): verify Ed25519 signature + expiry + hostname ∈ domains. Needs no
 *     network. An app can boot and validate even if the license server is down.
 *   - ONLINE (throttle to ~daily): POST /heartbeat to pick up renewals (refreshedToken),
 *     revocation, and install-cap enforcement. Resets the offline grace clock.
 *
 * Grace: if the server is unreachable, the app keeps running on its cached token for
 * `unreachableGraceDays` (default 7) since the last successful online check, then blocks.
 * After expiry, it shows a warning for `expiryGraceDays` (default 7), then blocks.
 */
import crypto from "node:crypto";

export type LicensePayload = {
  jti: string;
  tid: string;
  iss: string;
  product: string;
  tenant: string;
  domains: string[];
  ips: string[];
  maxInstalls: number;
  plan: string;
  features?: unknown;
  iat: number;
  exp: number;
  ver: number;
};

export type LicenseStatus =
  | "active"        // valid, confirmed
  | "grace"         // running but warn the operator (offline too long / past expiry within grace)
  | "expired"       // past expiry beyond grace → block
  | "revoked"       // server revoked → block
  | "invalid"       // bad signature / malformed → block
  | "domain_mismatch" // token not licensed for this hostname → block
  | "install_blocked" // exceeded maxInstalls → block
  | "ip_mismatch"     // hosting IP not in the license's allowed set (server-enforced) → block
  | "grace_expired";  // offline beyond grace, cannot confirm → block

export type CheckResult = {
  ok: boolean;                 // may the app run?
  status: LicenseStatus;
  reason?: string;
  expiresAt?: string;          // ISO
  daysRemaining?: number;
  refreshedToken?: string;     // PERSIST this if present (renewal picked up)
  nextLastGoodCheck?: number;  // PERSIST this (unix ms) when an online check succeeded
  checkedOnline: boolean;
};

export type CheckConfig = {
  token: string;               // the license key
  publicKeyPem: string;        // Ed25519 SPKI PEM (fetch once from <server>/api/v1/pubkey)
  hostname: string;            // e.g. new URL(req).host, or process.env.APP_HOST
  serverUrl: string;           // license server base, e.g. https://licenses.mg
  installId: string;           // stable random id; generate once, persist (see makeInstallId)
  lastGoodCheck?: number;      // unix ms of last successful online check (persisted)
  onlineEveryMs?: number;      // throttle online checks (default 24h)
  unreachableGraceDays?: number; // default 7
  expiryGraceDays?: number;    // default 7
  fetchTimeoutMs?: number;     // default 4000
};

const DAY = 86_400_000;

// --- offline primitives ---
function b64uToBuf(s: string): Buffer {
  return Buffer.from(s, "base64url");
}

export function decodeToken(token: string): LicensePayload | null {
  try {
    const p = token.split(".")[1];
    return p ? (JSON.parse(b64uToBuf(p).toString("utf8")) as LicensePayload) : null;
  } catch {
    return null;
  }
}

export function verifySignature(token: string, publicKeyPem: string): boolean {
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  try {
    return crypto.verify(
      null,
      Buffer.from(`${parts[0]}.${parts[1]}`),
      crypto.createPublicKey(publicKeyPem),
      b64uToBuf(parts[2])
    );
  } catch {
    return false;
  }
}

function hostnameAllowed(host: string, domains: string[]): boolean {
  if (domains.includes("*")) return true;
  const h = host.toLowerCase().split(":")[0];
  return domains.some((d) => d.toLowerCase().split(":")[0] === h);
}

/** Pure offline verdict: signature + issuer + domain + expiry. No network. */
export function verifyOffline(
  token: string,
  publicKeyPem: string,
  hostname: string
): { status: LicenseStatus; payload?: LicensePayload } {
  if (!verifySignature(token, publicKeyPem)) return { status: "invalid" };
  const payload = decodeToken(token);
  if (!payload || payload.iss !== "MGLicenses") return { status: "invalid" };
  if (!hostnameAllowed(hostname, payload.domains)) return { status: "domain_mismatch", payload };
  if (payload.exp * 1000 <= Date.now()) return { status: "expired", payload };
  return { status: "active", payload };
}

// --- helper: stable install id (persist the return value once) ---
export function makeInstallId(): string {
  return crypto.randomUUID();
}

function withinExpiryGrace(payload: LicensePayload, graceDays: number): boolean {
  return Date.now() - payload.exp * 1000 <= graceDays * DAY;
}
function daysRemaining(payload: LicensePayload): number {
  return Math.ceil((payload.exp * 1000 - Date.now()) / DAY);
}

/**
 * Full hybrid check. Offline-verify, then (throttled) confirm online.
 * The caller must persist `refreshedToken` and `nextLastGoodCheck` when present.
 */
export async function checkLicense(cfg: CheckConfig): Promise<CheckResult> {
  const {
    token,
    publicKeyPem,
    hostname,
    serverUrl,
    installId,
    lastGoodCheck,
    onlineEveryMs = DAY,
    unreachableGraceDays = 7,
    expiryGraceDays = 7,
    fetchTimeoutMs = 4000,
  } = cfg;

  const off = verifyOffline(token, publicKeyPem, hostname);

  // Hard offline failures never get a network reprieve.
  if (off.status === "invalid") return { ok: false, status: "invalid", checkedOnline: false };
  if (off.status === "domain_mismatch")
    return { ok: false, status: "domain_mismatch", checkedOnline: false };

  const payload = off.payload!;
  const expiresAt = new Date(payload.exp * 1000).toISOString();
  const now = Date.now();

  // `lastGoodCheck` is caller-persisted → attacker-controllable on a licensed host. Clamp a
  // future value (can't be trusted) so it can't disable phone-home or extend grace.
  const safeLastGood = lastGoodCheck && lastGoodCheck <= now ? lastGoodCheck : undefined;
  // Anchor the unreachable-grace window to something the attacker can't push forward:
  // the last CONFIRMED check, or — if we've never confirmed — the SERVER-SIGNED token
  // issue time (iat). This forces every install to confirm online at least once within
  // the grace window, so revocation/install-cap can't be dodged by staying offline.
  const graceAnchor = safeLastGood ?? payload.iat * 1000;

  // Decide whether to hit the network this call (throttle on the trusted timestamp).
  const due = !safeLastGood || now - safeLastGood >= onlineEveryMs;

  if (due) {
    const online = await heartbeat(serverUrl, token, installId, hostname, fetchTimeoutMs);
    if (online.reached) {
      if (online.revoked) return { ok: false, status: "revoked", checkedOnline: true, nextLastGoodCheck: now };
      if (online.ipBlocked)
        return { ok: false, status: "ip_mismatch", checkedOnline: true, nextLastGoodCheck: now };
      if (online.installBlocked)
        return { ok: false, status: "install_blocked", checkedOnline: true, nextLastGoodCheck: now };
      if (online.expired) {
        const grace = withinExpiryGrace(payload, expiryGraceDays);
        return {
          ok: grace,
          status: grace ? "grace" : "expired",
          expiresAt,
          checkedOnline: true,
          nextLastGoodCheck: now,
          refreshedToken: online.refreshedToken,
        };
      }
      return {
        ok: true,
        status: "active",
        expiresAt: online.expiresAt ?? expiresAt,
        daysRemaining: daysRemaining(payload),
        checkedOnline: true,
        nextLastGoodCheck: now,
        refreshedToken: online.refreshedToken,
      };
    }
    // Unreachable → fall through to offline + grace handling below.
  }

  // Offline path (throttled-off, or server unreachable). Block if we haven't confirmed
  // within the grace window — measured from the last confirmed check, or from the signed
  // token issue time if we've never confirmed. This fails CLOSED for never-online installs.
  if (now - graceAnchor > unreachableGraceDays * DAY) {
    return { ok: false, status: "grace_expired", expiresAt, checkedOnline: false };
  }

  if (off.status === "expired") {
    const grace = withinExpiryGrace(payload, expiryGraceDays);
    return { ok: grace, status: grace ? "grace" : "expired", expiresAt, checkedOnline: false };
  }

  // Valid offline within grace. Flag as "grace" until an online check has confirmed at least once.
  return {
    ok: true,
    status: safeLastGood ? "active" : "grace",
    expiresAt,
    daysRemaining: daysRemaining(payload),
    checkedOnline: false,
  };
}

type HeartbeatResult = {
  reached: boolean;
  revoked?: boolean;
  expired?: boolean;
  installBlocked?: boolean;
  ipBlocked?: boolean;
  expiresAt?: string;
  refreshedToken?: string;
};

async function heartbeat(
  serverUrl: string,
  token: string,
  installId: string,
  hostname: string,
  timeoutMs: number
): Promise<HeartbeatResult> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(`${serverUrl.replace(/\/$/, "")}/api/v1/heartbeat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ token, installId, hostname }),
      signal: ctrl.signal,
    });
    if (!r.ok) return { reached: false };
    const j = (await r.json()) as {
      revoked?: boolean;
      expired?: boolean;
      installBlocked?: boolean;
      ipBlocked?: boolean;
      expiresAt?: string;
      refreshedToken?: string;
    };
    return {
      reached: true,
      revoked: j.revoked,
      expired: j.expired,
      installBlocked: j.installBlocked,
      ipBlocked: j.ipBlocked,
      expiresAt: j.expiresAt,
      refreshedToken: j.refreshedToken,
    };
  } catch {
    return { reached: false };
  } finally {
    clearTimeout(t);
  }
}
