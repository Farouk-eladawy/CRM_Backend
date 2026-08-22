import { Injectable, Logger } from '@nestjs/common';
import { Readable } from 'stream';
import { PrismaService } from '../prisma/prisma.service.js';

/** Drive file IDs are alphanumeric+underscore+hyphen, no slashes — used to detect new vs legacy URLs */
export function isDriveFileId(value: string): boolean {
  return /^[A-Za-z0-9_-]{20,}$/.test(value);
}

interface DriveConfig {
  enabled: boolean;
  oauthClientId: string;
  oauthClientSecret: string;
  oauthRefreshToken: string;
  rootFolderId: string;
}

@Injectable()
export class GoogleDriveService {
  private readonly logger = new Logger(GoogleDriveService.name);

  /** In-process folder ID cache: key → Drive folder ID */
  private folderCache = new Map<string, string>();

  /** Short-lived config cache to avoid repeated DB hits within a single request */
  private configCache: { value: DriveConfig | null; expiresAt: number } | null = null;
  private readonly CONFIG_TTL_MS = 30_000; // 30 seconds

  constructor(private readonly prisma: PrismaService) {}

  // ──────────────────────────────────────────────────────────────────────────
  // Config helpers
  // ──────────────────────────────────────────────────────────────────────────

  async getConfig(): Promise<DriveConfig | null> {
    const now = Date.now();
    if (this.configCache && this.configCache.expiresAt > now) {
      return this.configCache.value;
    }

    const row = await this.prisma.googleDriveSettings.findFirst();
    const value =
      !row ||
      !row.enabled ||
      !row.oauthClientId ||
      !row.oauthClientSecret ||
      !row.oauthRefreshToken ||
      !row.rootFolderId
        ? null
        : {
            enabled: row.enabled,
            oauthClientId: row.oauthClientId,
            oauthClientSecret: row.oauthClientSecret,
            oauthRefreshToken: row.oauthRefreshToken,
            rootFolderId: row.rootFolderId,
          };

    this.configCache = { value, expiresAt: now + this.CONFIG_TTL_MS };
    return value;
  }

  /** Invalidate folder cache — call after settings update */
  clearCache() {
    this.folderCache.clear();
    this.configCache = null;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // OAuth2 client factory
  // ──────────────────────────────────────────────────────────────────────────

  private async getOAuth2Client(clientId: string, clientSecret: string, redirectUri?: string) {
    const { google } = await import('googleapis');
    return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
  }

  private async getDrive(config: DriveConfig) {
    const { google } = await import('googleapis');
    const oauth2Client = await this.getOAuth2Client(config.oauthClientId, config.oauthClientSecret);
    oauth2Client.setCredentials({ refresh_token: config.oauthRefreshToken });
    return google.drive({ version: 'v3', auth: oauth2Client });
  }

  // ──────────────────────────────────────────────────────────────────────────
  // OAuth flow helpers (called from settings controller)
  // ──────────────────────────────────────────────────────────────────────────

  async generateAuthUrl(redirectUri: string): Promise<string> {
    const row = await this.prisma.googleDriveSettings.findFirst();
    if (!row?.oauthClientId || !row?.oauthClientSecret) {
      throw new Error('Save Client ID and Client Secret first before connecting.');
    }

    const oauth2Client = await this.getOAuth2Client(row.oauthClientId, row.oauthClientSecret, redirectUri);
    return oauth2Client.generateAuthUrl({
      access_type: 'offline',
      prompt: 'consent',   // force refresh_token on every consent
      scope: ['https://www.googleapis.com/auth/drive'],
    });
  }

  async exchangeCode(code: string, redirectUri: string): Promise<void> {
    const row = await this.prisma.googleDriveSettings.findFirst();
    if (!row?.oauthClientId || !row?.oauthClientSecret) {
      throw new Error('Client credentials not found. Save them first.');
    }

    const oauth2Client = await this.getOAuth2Client(row.oauthClientId, row.oauthClientSecret, redirectUri);
    const { tokens } = await oauth2Client.getToken(code);

    if (!tokens.refresh_token) {
      throw new Error(
        'Google did not return a refresh token. ' +
        'Revoke app access at myaccount.google.com/permissions and try connecting again.',
      );
    }

    await this.prisma.googleDriveSettings.update({
      where: { id: row.id },
      data: { oauthRefreshToken: tokens.refresh_token },
    });

    this.clearCache();
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Folder management
  // ──────────────────────────────────────────────────────────────────────────

  private async getOrCreateFolder(drive: any, name: string, parentId: string): Promise<string> {
    const cacheKey = `${parentId}::${name}`;
    if (this.folderCache.has(cacheKey)) return this.folderCache.get(cacheKey)!;

    const search = await drive.files.list({
      q: `name='${name}' and mimeType='application/vnd.google-apps.folder' and '${parentId}' in parents and trashed=false`,
      fields: 'files(id)',
      spaces: 'drive',
      supportsAllDrives: true,
      includeItemsFromAllDrives: true,
    });

    if (search.data.files?.length) {
      const id = search.data.files[0].id as string;
      this.folderCache.set(cacheKey, id);
      return id;
    }

    const created = await drive.files.create({
      supportsAllDrives: true,
      requestBody: {
        name,
        mimeType: 'application/vnd.google-apps.folder',
        parents: [parentId],
      },
      fields: 'id',
    });

    const id = created.data.id as string;
    this.folderCache.set(cacheKey, id);
    return id;
  }

  async resolveEvidenceFolder(
    drive: any,
    rootFolderId: string,
    jobRef: string,
    type: 'Rep Evidence' | 'Driver Evidence' | 'No-Show Evidence',
  ): Promise<string> {
    const jobFolder = await this.getOrCreateFolder(drive, jobRef, rootFolderId);
    return this.getOrCreateFolder(drive, type, jobFolder);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Upload
  // ──────────────────────────────────────────────────────────────────────────

  async uploadFile(
    buffer: Buffer,
    filename: string,
    mimeType: string,
    jobId: string,
    type: 'rep' | 'driver' | 'no-show',
  ): Promise<string | null> {
    const config = await this.getConfig();
    if (!config) return null;

    try {
      const drive = await this.getDrive(config);

      const job = await this.prisma.trafficJob.findUnique({
        where: { id: jobId },
        select: { internalRef: true },
      });
      const jobRef = job?.internalRef ?? jobId;

      const folderLabel =
        type === 'rep' ? 'Rep Evidence' :
        type === 'driver' ? 'Driver Evidence' :
        'No-Show Evidence';

      const folderId = await this.resolveEvidenceFolder(
        drive,
        config.rootFolderId,
        jobRef,
        folderLabel as any,
      );

      const stream = Readable.from(buffer);
      const res = await drive.files.create({
        supportsAllDrives: true,
        requestBody: { name: filename, parents: [folderId] },
        media: { mimeType, body: stream },
        fields: 'id',
      });

      return res.data.id as string;
    } catch (err) {
      this.logger.error('Drive upload failed', err);
      return null;
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Download (for PDF embed + proxy)
  // ──────────────────────────────────────────────────────────────────────────

  async getFileBuffer(fileId: string): Promise<Buffer | null> {
    const config = await this.getConfig();
    if (!config) return null;

    try {
      const drive = await this.getDrive(config);
      const res = await drive.files.get(
        { fileId, alt: 'media', supportsAllDrives: true },
        { responseType: 'arraybuffer' },
      );
      return Buffer.from(res.data as ArrayBuffer);
    } catch (err) {
      this.logger.error(`Drive download failed for ${fileId}`, err);
      return null;
    }
  }

  async getFileStream(fileId: string): Promise<{ stream: Readable; mimeType: string } | null> {
    const config = await this.getConfig();
    if (!config) return null;

    try {
      const drive = await this.getDrive(config);
      const meta = await drive.files.get({ fileId, fields: 'mimeType', supportsAllDrives: true });
      const mimeType = (meta.data.mimeType as string) || 'application/octet-stream';

      const res = await drive.files.get(
        { fileId, alt: 'media', supportsAllDrives: true },
        { responseType: 'stream' },
      );

      return { stream: res.data as Readable, mimeType };
    } catch (err) {
      this.logger.error(`Drive stream failed for ${fileId}`, err);
      return null;
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Test connection
  // ──────────────────────────────────────────────────────────────────────────

  async testConnection(): Promise<{ ok: boolean; message: string }> {
    const config = await this.getConfig();
    if (!config) {
      return { ok: false, message: 'Google Drive is not configured or not enabled.' };
    }

    try {
      const drive = await this.getDrive(config);
      const res = await drive.files.get({
        fileId: config.rootFolderId,
        fields: 'id,name,mimeType',
        supportsAllDrives: true,
      });

      if (res.data.mimeType !== 'application/vnd.google-apps.folder') {
        return { ok: false, message: `"${res.data.name}" is not a folder. Check the Root Folder ID.` };
      }

      return { ok: true, message: `Connected. Root folder: "${res.data.name}"` };
    } catch (err: any) {
      const msg = err?.errors?.[0]?.message || err?.message || 'Unknown error';
      return { ok: false, message: `Connection failed: ${msg}` };
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Migration — move existing /uploads/ records to Drive
  // ──────────────────────────────────────────────────────────────────────────

  async migrateLocalFilesToDrive(): Promise<{
    total: number;
    migrated: number;
    skipped: number;
    errors: number;
    details: string[];
  }> {
    const config = await this.getConfig();
    if (!config) {
      return { total: 0, migrated: 0, skipped: 0, errors: 0, details: ['Drive not configured or not enabled.'] };
    }

    const drive = await this.getDrive(config);
    const fs = await import('fs');
    const path = await import('path');

    let migrated = 0;
    let skipped = 0;
    let errors = 0;
    const details: string[] = [];

    type EvidenceModel = 'noShowEvidence' | 'inPlaceEvidence' | 'completedEvidence';

    const models: { model: EvidenceModel; type: 'rep' | 'driver' | 'no-show' }[] = [
      { model: 'noShowEvidence', type: 'no-show' },
      { model: 'inPlaceEvidence', type: 'rep' },
      { model: 'completedEvidence', type: 'driver' },
    ];

    for (const { model, type } of models) {
      const records = await (this.prisma[model] as any).findMany({
        include: { trafficJob: { select: { internalRef: true } } },
      });

      for (const record of records) {
        const oldUrls: string[] = record.imageUrls ?? [];
        const newUrls: string[] = [];
        let changed = false;

        for (const url of oldUrls) {
          if (!url.startsWith('/uploads/')) {
            newUrls.push(url);
            continue;
          }

          const localPath = path.default.join(process.cwd(), url.replace(/^\//, ''));
          if (!fs.default.existsSync(localPath)) {
            details.push(`MISSING: ${url}`);
            newUrls.push(url);
            errors++;
            continue;
          }

          try {
            const buffer = fs.default.readFileSync(localPath);
            const filename = path.default.basename(localPath);
            const mimeType = filename.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';

            const folderLabel =
              type === 'rep' ? 'Rep Evidence' :
              type === 'driver' ? 'Driver Evidence' :
              'No-Show Evidence';

            const folderId = await this.resolveEvidenceFolder(
              drive,
              config.rootFolderId,
              record.trafficJob.internalRef,
              folderLabel as any,
            );

            const stream = Readable.from(buffer);
            const res = await drive.files.create({
              supportsAllDrives: true,
              requestBody: { name: filename, parents: [folderId] },
              media: { mimeType, body: stream },
              fields: 'id',
            });

            newUrls.push(res.data.id as string);
            changed = true;
            migrated++;
            details.push(`OK: ${url} → ${res.data.id}`);
          } catch (err: any) {
            details.push(`ERROR: ${url} — ${err?.message}`);
            newUrls.push(url);
            errors++;
          }
        }

        if (changed) {
          await (this.prisma[model] as any).update({
            where: { id: record.id },
            data: { imageUrls: newUrls },
          });
        } else {
          skipped++;
        }
      }
    }

    return { total: migrated + skipped + errors, migrated, skipped, errors, details };
  }
}
