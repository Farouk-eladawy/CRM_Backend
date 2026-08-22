import sharp from 'sharp';

export interface StampMeta {
  rep?: string | null;
  driver?: string | null;
  status?: string | null;
  portalStatus?: string | null;
}

/**
 * Burn date/time (Cairo timezone) + GPS coordinates + optional rep/driver/status
 * onto an image buffer. Auto-rotates based on EXIF before compositing.
 * Returns a JPEG buffer.
 *
 * Font: "DejaVu Sans" installed via font-dejavu Alpine package in the
 * production Dockerfile — librsvg resolves it from the system font cache.
 */
export async function stampEvidenceImage(
  buffer: Buffer,
  lat: number | null | undefined,
  lng: number | null | undefined,
  date?: Date,
  meta?: StampMeta,
): Promise<Buffer> {
  const rotated = await sharp(buffer).rotate().toBuffer();
  const m = await sharp(rotated).metadata();
  const w = m.width ?? 1280;
  const h = m.height ?? 960;

  const now = date ?? new Date();
  const dateLine = now.toLocaleString('en-GB', {
    timeZone: 'Africa/Cairo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const gpsLine =
    lat != null && lng != null
      ? `GPS: ${lat.toFixed(6)}, ${lng.toFixed(6)}`
      : 'GPS: Not captured';

  const repLine    = meta?.rep    ? `Rep: ${meta.rep}` : null;
  const driverLine = meta?.driver ? `Driver: ${meta.driver}` : null;
  const peopleLine = [repLine, driverLine].filter(Boolean).join('   |   ') || null;
  const statusLine = meta?.status ? `Job Status: ${meta.status.replace(/_/g, ' ')}` : null;
  const portalLine = meta?.portalStatus ?? null;

  const extraLines = [peopleLine, statusLine, portalLine].filter(Boolean) as string[];
  const totalLines = 2 + extraLines.length;

  const fontSize = Math.max(16, Math.min(52, Math.round(w * 0.022)));
  const lineH    = Math.round(fontSize * 1.6);
  const pad      = Math.round(fontSize * 0.6);
  const bgH      = lineH * totalLines + pad * 2;

  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  const baseY = h - bgH + pad + lineH - Math.round(fontSize * 0.2);

  let textNodes =
    `<text x="${pad}" y="${baseY}" fill="#FFD700" font-family="DejaVu Sans,sans-serif" font-size="${fontSize}" font-weight="bold">${esc(dateLine)}</text>` +
    `<text x="${pad}" y="${baseY + lineH}" fill="#FFD700" font-family="DejaVu Sans,sans-serif" font-size="${fontSize}" font-weight="bold">${esc(gpsLine)}</text>`;

  extraLines.forEach((line, i) => {
    textNodes += `<text x="${pad}" y="${baseY + lineH * (i + 2)}" fill="#FFFFFF" font-family="DejaVu Sans,sans-serif" font-size="${fontSize}" font-weight="bold">${esc(line)}</text>`;
  });

  const svg = Buffer.from(
    `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">` +
      `<rect x="0" y="${h - bgH}" width="${w}" height="${bgH}" fill="rgba(0,0,0,0.65)"/>` +
      textNodes +
    `</svg>`,
  );

  return sharp(rotated)
    .composite([{ input: svg, blend: 'over' }])
    .jpeg({ quality: 88 })
    .toBuffer();
}
