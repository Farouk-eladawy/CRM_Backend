import {
  Body,
  Controller,
  Get,
  Patch,
  Post,
  UploadedFile,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { diskStorage } from 'multer';
import * as path from 'path';
import * as fs from 'fs';
import { SettingsService } from './settings.service.js';
import { UpdateSystemSettingsDto } from './dto/update-system-settings.dto.js';
import { UpdateCompanySettingsDto } from './dto/update-company-settings.dto.js';
import { UpdateEmailSettingsDto } from './dto/update-email-settings.dto.js';
import { UpdateWebsiteSettingsDto } from './dto/update-website-settings.dto.js';
import { UpdateGoogleDriveSettingsDto, GoogleDriveAuthUrlDto, GoogleDriveExchangeCodeDto } from './dto/update-google-drive-settings.dto.js';
import { EmailService } from '../email/email.service.js';
import { GoogleDriveService } from '../google-drive/google-drive.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';

/** Ensure the uploads directory exists at startup. */
const uploadsDir = path.join(process.cwd(), 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

/** Shared multer storage config for file uploads. */
const uploadStorage = diskStorage({
  destination: (_req, _file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (_req, file, cb) => {
    const uniqueName = Date.now() + '-' + file.originalname;
    cb(null, uniqueName);
  },
});

@Controller('settings')
@UseGuards(JwtAuthGuard)
export class SettingsController {
  constructor(
    private readonly settingsService: SettingsService,
    private readonly emailService: EmailService,
    private readonly googleDriveService: GoogleDriveService,
  ) {}

  // ──────────────────────────────────────────────
  // GET /settings/system — retrieve system settings
  // ──────────────────────────────────────────────

  @Get('system')
  async getSystemSettings() {
    return this.settingsService.getSystemSettings();
  }

  // ──────────────────────────────────────────────
  // PATCH /settings/system — update system settings (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch('system')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async updateSystemSettings(@Body() dto: UpdateSystemSettingsDto) {
    return this.settingsService.updateSystemSettings(dto);
  }

  // ──────────────────────────────────────────────
  // POST /settings/system/inner-bg — upload dashboard inner background image (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('system/inner-bg')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadInnerBgImage(@UploadedFile() file: any) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateInnerBgImage(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/system/login-bg — upload login background image (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('system/login-bg')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadLoginBgImage(@UploadedFile() file: any) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateLoginBgImage(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/system/login-logo — upload login logo image (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('system/login-logo')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadLoginLogoImage(@UploadedFile() file: any) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateLoginLogoImage(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // GET /settings/license-status — check license validity (authenticated)
  // ──────────────────────────────────────────────

  @Get('license-status')
  async getLicenseStatus() {
    return this.settingsService.getLicenseStatus();
  }

  // POST /settings/license-recheck — force an immediate online verification (ADMIN)
  @Post('license-recheck')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async recheckLicense() {
    return this.settingsService.recheckLicense();
  }

  // ──────────────────────────────────────────────
  // POST /settings/activate-license — activate/replace the company license key.
  // ADMIN only: it overwrites companySettings.licenseKey, so it must not be
  // reachable by every authenticated principal (drivers, reps, B2C clients).
  // ──────────────────────────────────────────────
  @Post('activate-license')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async activateLicense(@Body('key') key: string) {
    return this.settingsService.activateLicense(key);
  }

  // ──────────────────────────────────────────────
  // GET /settings/company — retrieve company settings
  // ──────────────────────────────────────────────

  @Get('company')
  async getCompanySettings() {
    return this.settingsService.getCompanySettings();
  }

  // ──────────────────────────────────────────────
  // PATCH /settings/company — update company settings (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch('company')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async updateCompanySettings(@Body() dto: UpdateCompanySettingsDto) {
    return this.settingsService.updateCompanySettings(dto);
  }

  // ──────────────────────────────────────────────
  // POST /settings/company/logo — upload company logo (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('company/logo')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.uploadLogo')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadLogo(@UploadedFile() file: any /* Express.Multer.File */) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateLogo(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/company/favicon — upload favicon (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('company/favicon')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.uploadFavicon')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadFavicon(@UploadedFile() file: any /* Express.Multer.File */) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateFavicon(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // GET /settings/email — retrieve email/SMTP settings
  // ──────────────────────────────────────────────

  @Get('email')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async getEmailSettings() {
    return this.settingsService.getEmailSettings();
  }

  // ──────────────────────────────────────────────
  // PATCH /settings/email — update email/SMTP settings (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch('email')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async updateEmailSettings(@Body() dto: UpdateEmailSettingsDto) {
    const result = await this.settingsService.updateEmailSettings(dto);
    // Force reload the SMTP transporter with new settings
    this.emailService.reloadTransporter();
    return result;
  }

  // ──────────────────────────────────────────────
  // POST /settings/email/test — send a test email (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('email/test')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async sendTestEmail(@Body() body: { email: string }) {
    await this.emailService.sendTestEmail(body.email);
    return { success: true };
  }

  // ──────────────────────────────────────────────
  // GET /settings/website — retrieve website CMS settings (ADMIN only)
  // ──────────────────────────────────────────────

  @Get('website')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async getWebsiteSettings() {
    return this.settingsService.getWebsiteSettings();
  }

  // ──────────────────────────────────────────────
  // PATCH /settings/website — update website CMS settings (ADMIN only)
  // ──────────────────────────────────────────────

  @Patch('website')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async updateWebsiteSettings(@Body() dto: UpdateWebsiteSettingsDto) {
    return this.settingsService.updateWebsiteSettings(dto);
  }

  // ──────────────────────────────────────────────
  // POST /settings/website/logo — upload website logo (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('website/logo')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.uploadLogo')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadSiteLogo(@UploadedFile() file: any /* Express.Multer.File */) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateSiteLogo(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/website/favicon — upload website favicon (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('website/favicon')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.uploadFavicon')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadSiteFavicon(@UploadedFile() file: any /* Express.Multer.File */) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateSiteFavicon(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/website/hero-image — upload hero background image (ADMIN only)
  // ──────────────────────────────────────────────

  @Post('website/hero-image')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  @UseInterceptors(FileInterceptor('file', { storage: uploadStorage }))
  async uploadHeroImage(@UploadedFile() file: any /* Express.Multer.File */) {
    const url = '/uploads/' + file.filename;
    await this.settingsService.updateHeroImage(url);
    return { url };
  }

  // ──────────────────────────────────────────────
  // GET /settings/google-drive
  // ──────────────────────────────────────────────

  @Get('google-drive')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async getGoogleDriveSettings() {
    return this.settingsService.getGoogleDriveSettings();
  }

  // ──────────────────────────────────────────────
  // PATCH /settings/google-drive — save client ID / secret / folder ID
  // ──────────────────────────────────────────────

  @Patch('google-drive')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async updateGoogleDriveSettings(@Body() dto: UpdateGoogleDriveSettingsDto) {
    const result = await this.settingsService.updateGoogleDriveSettings(dto);
    this.googleDriveService.clearCache();
    return result;
  }

  // ──────────────────────────────────────────────
  // POST /settings/google-drive/auth-url
  // Returns the Google OAuth consent URL for the admin to open
  // ──────────────────────────────────────────────

  @Post('google-drive/auth-url')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async getGoogleDriveAuthUrl(@Body() dto: GoogleDriveAuthUrlDto) {
    const url = await this.googleDriveService.generateAuthUrl(dto.redirectUri);
    return { url };
  }

  // ──────────────────────────────────────────────
  // POST /settings/google-drive/exchange-code
  // Exchanges the one-time Google auth code for a refresh token
  // ──────────────────────────────────────────────

  @Post('google-drive/exchange-code')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async exchangeGoogleDriveCode(@Body() dto: GoogleDriveExchangeCodeDto) {
    await this.googleDriveService.exchangeCode(dto.code, dto.redirectUri);
    return { ok: true };
  }

  // ──────────────────────────────────────────────
  // POST /settings/google-drive/disconnect
  // Clears the stored refresh token
  // ──────────────────────────────────────────────

  @Post('google-drive/disconnect')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async disconnectGoogleDrive() {
    await this.settingsService.disconnectGoogleDrive();
    this.googleDriveService.clearCache();
    return { ok: true };
  }

  // ──────────────────────────────────────────────
  // POST /settings/google-drive/test
  // ──────────────────────────────────────────────

  @Post('google-drive/test')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async testGoogleDriveConnection() {
    return this.googleDriveService.testConnection();
  }

  // ──────────────────────────────────────────────
  // POST /settings/google-drive/migrate
  // ──────────────────────────────────────────────

  @Post('google-drive/migrate')
  @UseGuards(RolesGuard, PermissionsGuard)
  @Roles('ADMIN')
  @Permissions('company.editSettings')
  async migrateEvidenceToDrive() {
    return this.googleDriveService.migrateLocalFilesToDrive();
  }
}
