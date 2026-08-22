/**
 * One-time script: re-stamp all existing evidence images with their
 * original GPS coordinates and createdAt timestamp.
 *
 * Run from /app inside the backend container:
 *   node scripts/restamp-evidence.mjs
 *
 * The script replaces Drive file content in-place (file ID unchanged,
 * so no DB updates needed).
 */

import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
import sharp from 'sharp';
import { google } from 'googleapis';
import { Readable } from 'stream';

// Font is installed system-wide via font-dejavu Alpine package.
// librsvg resolves "DejaVu Sans" from the fontconfig cache.

// ── Drive file ID detection ───────────────────────────────────────────────
function isDriveFileId(v) {
  return /^[A-Za-z0-9_-]{20,}$/.test(v);
}

// ── Stamp function (mirrors stamp-image.ts) ───────────────────────────────
async function stampImage(buffer, lat, lng, date) {
  const rotated = await sharp(buffer).rotate().toBuffer();
  const meta = await sharp(rotated).metadata();
  const w = meta.width ?? 1280;
  const h = meta.height ?? 960;

  const now = date ?? new Date();
  const dateLine = now.toLocaleString('en-GB', {
    timeZone: 'Africa/Cairo',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });
  const gpsLine = `GPS: ${Number(lat).toFixed(6)}, ${Number(lng).toFixed(6)}`;

  const fontSize = Math.max(16, Math.min(52, Math.round(w * 0.022)));
  const lineH = Math.round(fontSize * 1.6);
  const pad = Math.round(fontSize * 0.6);
  const bgH = lineH * 2 + pad * 2;
  const line1Y = h - bgH + pad + lineH - Math.round(fontSize * 0.2);
  const line2Y = line1Y + lineH;

  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  const svg = Buffer.from(
    `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">` +
    `<rect x="0" y="${h - bgH}" width="${w}" height="${bgH}" fill="rgba(0,0,0,0.65)"/>` +
    `<text x="${pad}" y="${line1Y}" fill="#FFD700" font-family="DejaVu Sans,sans-serif" font-size="${fontSize}" font-weight="bold">${esc(dateLine)}</text>` +
    `<text x="${pad}" y="${line2Y}" fill="#FFD700" font-family="DejaVu Sans,sans-serif" font-size="${fontSize}" font-weight="bold">${esc(gpsLine)}</text>` +
    `</svg>`
  );

  return sharp(rotated).composite([{ input: svg, blend: 'over' }]).jpeg({ quality: 88 }).toBuffer();
}

// ── Drive helpers ─────────────────────────────────────────────────────────
async function getDrive(config) {
  const auth = new google.auth.OAuth2(config.oauthClientId, config.oauthClientSecret);
  auth.setCredentials({ refresh_token: config.oauthRefreshToken });
  return google.drive({ version: 'v3', auth });
}

async function downloadFile(drive, fileId) {
  const res = await drive.files.get(
    { fileId, alt: 'media', supportsAllDrives: true },
    { responseType: 'arraybuffer' }
  );
  return Buffer.from(res.data);
}

async function replaceFileContent(drive, fileId, buffer) {
  const stream = Readable.from(buffer);
  await drive.files.update({
    fileId,
    supportsAllDrives: true,
    media: { mimeType: 'image/jpeg', body: stream },
  });
}

// ── Main ──────────────────────────────────────────────────────────────────
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaPg(pool);
const prisma = new PrismaClient({ adapter });

async function processRecords(label, records, drive) {
  let stamped = 0, skipped = 0, failed = 0;

  for (const rec of records) {
    const driveIds = (rec.imageUrls ?? []).filter(isDriveFileId);
    if (driveIds.length === 0) { skipped++; continue; }

    for (const fileId of driveIds) {
      try {
        const original = await downloadFile(drive, fileId);
        const stamped_buf = await stampImage(
          original,
          Number(rec.gpsLatitude),
          Number(rec.gpsLongitude),
          new Date(rec.createdAt),
        );
        await replaceFileContent(drive, fileId, stamped_buf);
        stamped++;
        process.stdout.write('.');
      } catch (err) {
        failed++;
        console.error(`\n  FAIL ${fileId}: ${err.message}`);
      }
    }
  }

  console.log(`\n${label}: ${stamped} stamped, ${skipped} skipped (no Drive IDs), ${failed} failed`);
}

async function main() {
  // Load Drive config from DB
  const settings = await prisma.googleDriveSettings.findFirst();
  if (!settings?.enabled || !settings.oauthRefreshToken) {
    console.error('Google Drive not configured or not enabled. Aborting.');
    process.exit(1);
  }

  const drive = await getDrive(settings);
  console.log('Drive connected. Starting restamp...\n');

  const [noShow, inPlace, completed] = await Promise.all([
    prisma.noShowEvidence.findMany({ select: { id: true, imageUrls: true, gpsLatitude: true, gpsLongitude: true, createdAt: true } }),
    prisma.inPlaceEvidence.findMany({ select: { id: true, imageUrls: true, gpsLatitude: true, gpsLongitude: true, createdAt: true } }),
    prisma.completedEvidence.findMany({ select: { id: true, imageUrls: true, gpsLatitude: true, gpsLongitude: true, createdAt: true } }),
  ]);

  console.log(`Records — NoShow: ${noShow.length}, InPlace: ${inPlace.length}, Completed: ${completed.length}`);
  console.log('Progress dots = each image stamped:\n');

  await processRecords('NoShowEvidence', noShow, drive);
  await processRecords('InPlaceEvidence', inPlace, drive);
  await processRecords('CompletedEvidence', completed, drive);

  console.log('\nDone.');
}

main()
  .catch(e => { console.error('Fatal:', e); process.exit(1); })
  .finally(async () => { await prisma.$disconnect(); await pool.end(); });
