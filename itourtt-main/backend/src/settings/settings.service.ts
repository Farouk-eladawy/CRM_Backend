import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';
import { UpdateSystemSettingsDto } from './dto/update-system-settings.dto.js';
import { UpdateCompanySettingsDto } from './dto/update-company-settings.dto.js';
import { UpdateEmailSettingsDto } from './dto/update-email-settings.dto.js';
import { UpdateWebsiteSettingsDto } from './dto/update-website-settings.dto.js';
import { UpdateGoogleDriveSettingsDto } from './dto/update-google-drive-settings.dto.js';
import { ConfigService } from '@nestjs/config';
import { checkLicense, makeInstallId, verifyOffline } from '../common/license-verify.js';
import { toLicenseStatus, normalizePublicKey, type LicenseStatus } from '../common/license.util.js';

/** Default values returned when no row exists yet. */
const SYSTEM_DEFAULTS = {
  theme: 'dark',
  primaryColor: '#3b82f6',
  accentColor: '#8b5cf6',
  sidebarColor: '#41004c',
  fontFamily: 'Geist',
  language: 'en',
  googleMapsApiKey: null as string | null,
  innerBgImageUrl: null as string | null,
  loginBgImageUrl: null as string | null,
  loginLogoUrl: null as string | null,
};

const EMAIL_DEFAULTS = {
  smtpHost: null as string | null,
  smtpPort: 587,
  smtpSecure: false,
  smtpUser: null as string | null,
  smtpPass: null as string | null,
  fromAddress: 'noreply@itour.local',
  notifyDispatchEmail: null as string | null,
  notifyTrafficEmail: null as string | null,
  disputeTo: null as string | null,
  disputeCc1: null as string | null,
  disputeCc2: null as string | null,
  disputeCc3: null as string | null,
  disputeSubject: null as string | null,
  disputeBody: null as string | null,
};

const COMPANY_DEFAULTS = {
  companyName: 'iTour TT',
  logoUrl: null,
  faviconUrl: null,
  reportHeaderHtml: null,
  reportFooterHtml: null,
  systemNotificationEmail: null as string | null,
};

const WEBSITE_DEFAULTS = {
  siteName: 'iTour Transfers',
  siteLogoUrl: null as string | null,
  siteFaviconUrl: null as string | null,
  fontFamily: 'Inter',
  primaryColor: '#3b82f6',
  accentColor: '#8b5cf6',
  heroGradientFrom: '#1a1a2e',
  heroGradientTo: '#0f3460',
  navBgColor: '#1a1a2e',
  footerBgColor: '#1a1a2e',
  headerPreset: 'default',
  footerPreset: 'default',
  heroTitle: 'Book Your Airport Transfer',
  heroSubtitle: 'Safe, comfortable, and reliable private transfers across Egypt.',
  heroCta1Text: 'Book Now',
  heroCta2Text: 'Track a Booking',
  heroImageUrl: null as string | null,
  featuresEnabled: true,
  featuresTitle: 'Why Choose Us?',
  featuresJson: null as any,
  contactEmail: null as string | null,
  contactPhone: null as string | null,
  contactWhatsapp: null as string | null,
  socialFacebook: null as string | null,
  socialInstagram: null as string | null,
  socialTwitter: null as string | null,
  opsNotificationEmails: null as string | null,
  financeNotificationEmails: null as string | null,
  bankPaymentEnabled: false,
  bankPaymentMessage: 'Bank payment integration coming soon!',
  onlinePaymentEnabled: true,
  cashOnArrivalEnabled: true,
  enableTwoWayTab: false,
  enableCityToCityTab: false,
  enableMapSelector: false,
  enableAiMode: false,
  bookingTabsOrder: 'ARR,DEP',
  metaTitle: null as string | null,
  metaDescription: null as string | null,
  navLinksJson: null as any,
};

@Injectable()
export class SettingsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
  ) {}

  // ──────────────────────────────────────────────
  // SYSTEM SETTINGS
  // ──────────────────────────────────────────────

  async getSystemSettings() {
    const settings = await this.prisma.systemSettings.findFirst();
    if (!settings) {
      return SYSTEM_DEFAULTS;
    }
    return settings;
  }

  async updateSystemSettings(dto: UpdateSystemSettingsDto) {
    const existing = await this.prisma.systemSettings.findFirst();

    if (existing) {
      return this.prisma.systemSettings.update({
        where: { id: existing.id },
        data: {
          ...(dto.theme !== undefined && { theme: dto.theme }),
          ...(dto.primaryColor !== undefined && { primaryColor: dto.primaryColor }),
          ...(dto.accentColor !== undefined && { accentColor: dto.accentColor }),
          ...(dto.sidebarColor !== undefined && { sidebarColor: dto.sidebarColor }),
          ...(dto.fontFamily !== undefined && { fontFamily: dto.fontFamily }),
          ...(dto.language !== undefined && { language: dto.language }),
          ...(dto.googleMapsApiKey !== undefined && { googleMapsApiKey: dto.googleMapsApiKey || null }),
        },
      });
    }

    return this.prisma.systemSettings.create({
      data: {
        theme: dto.theme ?? SYSTEM_DEFAULTS.theme,
        primaryColor: dto.primaryColor ?? SYSTEM_DEFAULTS.primaryColor,
        accentColor: dto.accentColor ?? SYSTEM_DEFAULTS.accentColor,
        sidebarColor: dto.sidebarColor ?? SYSTEM_DEFAULTS.sidebarColor,
        fontFamily: dto.fontFamily ?? SYSTEM_DEFAULTS.fontFamily,
        language: dto.language ?? SYSTEM_DEFAULTS.language,
        googleMapsApiKey: dto.googleMapsApiKey ?? SYSTEM_DEFAULTS.googleMapsApiKey,
      },
    });
  }

  // ──────────────────────────────────────────────
  // COMPANY SETTINGS
  // ──────────────────────────────────────────────

  async getCompanySettings() {
    const settings = await this.prisma.companySettings.findFirst();
    if (!settings) {
      return COMPANY_DEFAULTS;
    }
    return settings;
  }

  async updateCompanySettings(dto: UpdateCompanySettingsDto) {
    const existing = await this.prisma.companySettings.findFirst();

    const data: Record<string, unknown> = {};
    if (dto.companyName !== undefined) data.companyName = dto.companyName;
    if (dto.reportHeaderHtml !== undefined) data.reportHeaderHtml = dto.reportHeaderHtml;
    if (dto.reportFooterHtml !== undefined) data.reportFooterHtml = dto.reportFooterHtml;
    if (dto.licenseKey !== undefined) data.licenseKey = dto.licenseKey || null;
    if (dto.systemNotificationEmail !== undefined)
      data.systemNotificationEmail = dto.systemNotificationEmail?.trim() || null;

    if (existing) {
      return this.prisma.companySettings.update({
        where: { id: existing.id },
        data,
      });
    }

    return this.prisma.companySettings.create({
      data: {
        companyName: dto.companyName ?? COMPANY_DEFAULTS.companyName,
        reportHeaderHtml: dto.reportHeaderHtml ?? COMPANY_DEFAULTS.reportHeaderHtml,
        reportFooterHtml: dto.reportFooterHtml ?? COMPANY_DEFAULTS.reportFooterHtml,
        licenseKey: dto.licenseKey ?? null,
        systemNotificationEmail: dto.systemNotificationEmail?.trim() || null,
      },
    });
  }

  // ──────────────────────────────────────────────
  // LICENSE STATUS
  // ──────────────────────────────────────────────

  // Offline-verify (sig/domain/expiry) + throttled online heartbeat (renew/revoke/install cap).
  // The verifier hands back a token refresh + last-check timestamp we must persist.
  private noKeyStatus(): LicenseStatus {
    return {
      valid: false,
      expiresAt: null,
      daysRemaining: null,
      message: 'No license key configured',
      status: 'invalid',
      checkedOnline: false,
      lastCheckedAt: null,
    };
  }

  private async evaluate(
    settings: {
      id: string;
      licenseKey: string | null;
      installId: string | null;
      licenseLastCheck: Date | null;
    },
    opts?: { forceOnline?: boolean },
  ): Promise<LicenseStatus> {
    if (!settings.licenseKey) {
      return this.noKeyStatus();
    }

    const installId = settings.installId ?? makeInstallId();
    const result = await checkLicense({
      token: settings.licenseKey,
      publicKeyPem: normalizePublicKey(this.config.get<string>('LICENSE_PUBLIC_KEY')),
      hostname: this.config.get<string>('APP_HOST') ?? '',
      serverUrl: this.config.get<string>('LICENSE_SERVER_URL') ?? '',
      installId,
      lastGoodCheck: settings.licenseLastCheck?.getTime(),
      // Force an online round-trip when the operator hits "Re-check now" (bypass the ~daily throttle).
      onlineEveryMs: opts?.forceOnline ? 0 : undefined,
    });

    // Persist installId (first run), a picked-up renewal, and the last online-check time.
    const data: Record<string, unknown> = {};
    if (!settings.installId) data.installId = installId;
    if (result.refreshedToken) data.licenseKey = result.refreshedToken;
    if (result.nextLastGoodCheck) data.licenseLastCheck = new Date(result.nextLastGoodCheck);
    if (Object.keys(data).length) {
      await this.prisma.companySettings.update({ where: { id: settings.id }, data });
    }

    const lastCheck = result.nextLastGoodCheck
      ? new Date(result.nextLastGoodCheck)
      : settings.licenseLastCheck;
    return toLicenseStatus(result, lastCheck ? lastCheck.toISOString() : null);
  }

  async getLicenseStatus(): Promise<LicenseStatus> {
    const settings = await this.prisma.companySettings.findFirst();
    if (!settings) {
      return this.noKeyStatus();
    }
    return this.evaluate(settings);
  }

  /** Force an immediate online verification against the license server ("Re-check now" button). */
  async recheckLicense(): Promise<LicenseStatus> {
    const settings = await this.prisma.companySettings.findFirst();
    if (!settings) {
      return this.noKeyStatus();
    }
    return this.evaluate(settings, { forceOnline: true });
  }

  async activateLicense(key: string): Promise<LicenseStatus> {
    const trimmed = (key ?? '').trim();
    // Reject a clearly-invalid paste before it overwrites a possibly-working key.
    const off = verifyOffline(
      trimmed,
      normalizePublicKey(this.config.get<string>('LICENSE_PUBLIC_KEY')),
      this.config.get<string>('APP_HOST') ?? '',
    );
    if (off.status === 'invalid' || off.status === 'domain_mismatch') {
      return toLicenseStatus({ ok: false, status: off.status, checkedOnline: false });
    }

    const existing = await this.prisma.companySettings.findFirst();
    // Store the new key + reset the online-check clock, then confirm online (persists installId/refresh).
    const saved = existing
      ? await this.prisma.companySettings.update({
          where: { id: existing.id },
          data: { licenseKey: trimmed, licenseLastCheck: null },
        })
      : await this.prisma.companySettings.create({ data: { licenseKey: trimmed } });
    return this.evaluate(saved);
  }

  // ──────────────────────────────────────────────
  // FILE UPLOADS (logo / favicon)
  // ──────────────────────────────────────────────

  async updateLogo(fileUrl: string) {
    const existing = await this.prisma.companySettings.findFirst();

    if (existing) {
      return this.prisma.companySettings.update({
        where: { id: existing.id },
        data: { logoUrl: fileUrl },
      });
    }

    return this.prisma.companySettings.create({
      data: {
        companyName: COMPANY_DEFAULTS.companyName,
        logoUrl: fileUrl,
      },
    });
  }

  async updateFavicon(fileUrl: string) {
    const existing = await this.prisma.companySettings.findFirst();

    if (existing) {
      return this.prisma.companySettings.update({
        where: { id: existing.id },
        data: { faviconUrl: fileUrl },
      });
    }

    return this.prisma.companySettings.create({
      data: {
        companyName: COMPANY_DEFAULTS.companyName,
        faviconUrl: fileUrl,
      },
    });
  }

  // ──────────────────────────────────────────────
  // EMAIL SETTINGS
  // ──────────────────────────────────────────────

  async getEmailSettings() {
    const settings = await this.prisma.emailSettings.findFirst();
    if (!settings) {
      return EMAIL_DEFAULTS;
    }
    // Mask password for frontend display
    return {
      ...settings,
      smtpPass: settings.smtpPass ? '••••••••' : null,
    };
  }

  async updateEmailSettings(dto: UpdateEmailSettingsDto) {
    const existing = await this.prisma.emailSettings.findFirst();

    // Don't overwrite password if masked placeholder is sent
    const data: Record<string, unknown> = {};
    if (dto.smtpHost !== undefined) data.smtpHost = dto.smtpHost || null;
    if (dto.smtpPort !== undefined) data.smtpPort = dto.smtpPort;
    if (dto.smtpSecure !== undefined) data.smtpSecure = dto.smtpSecure;
    if (dto.smtpUser !== undefined) data.smtpUser = dto.smtpUser || null;
    if (dto.smtpPass !== undefined && dto.smtpPass !== '••••••••') {
      data.smtpPass = dto.smtpPass || null;
    }
    if (dto.fromAddress !== undefined) data.fromAddress = dto.fromAddress;
    if (dto.notifyDispatchEmail !== undefined) data.notifyDispatchEmail = dto.notifyDispatchEmail || null;
    if (dto.notifyTrafficEmail !== undefined) data.notifyTrafficEmail = dto.notifyTrafficEmail || null;
    if (dto.disputeTo !== undefined) data.disputeTo = dto.disputeTo || null;
    if (dto.disputeCc1 !== undefined) data.disputeCc1 = dto.disputeCc1 || null;
    if (dto.disputeCc2 !== undefined) data.disputeCc2 = dto.disputeCc2 || null;
    if (dto.disputeCc3 !== undefined) data.disputeCc3 = dto.disputeCc3 || null;
    if (dto.disputeSubject !== undefined) data.disputeSubject = dto.disputeSubject || null;
    if (dto.disputeBody !== undefined) data.disputeBody = dto.disputeBody || null;

    if (existing) {
      return this.prisma.emailSettings.update({
        where: { id: existing.id },
        data,
      });
    }

    return this.prisma.emailSettings.create({
      data: {
        smtpHost: dto.smtpHost ?? EMAIL_DEFAULTS.smtpHost,
        smtpPort: dto.smtpPort ?? EMAIL_DEFAULTS.smtpPort,
        smtpSecure: dto.smtpSecure ?? EMAIL_DEFAULTS.smtpSecure,
        smtpUser: dto.smtpUser ?? EMAIL_DEFAULTS.smtpUser,
        smtpPass: dto.smtpPass ?? EMAIL_DEFAULTS.smtpPass,
        fromAddress: dto.fromAddress ?? EMAIL_DEFAULTS.fromAddress,
        notifyDispatchEmail: dto.notifyDispatchEmail ?? EMAIL_DEFAULTS.notifyDispatchEmail,
        notifyTrafficEmail: dto.notifyTrafficEmail ?? EMAIL_DEFAULTS.notifyTrafficEmail,
        disputeTo: dto.disputeTo ?? EMAIL_DEFAULTS.disputeTo,
        disputeCc1: dto.disputeCc1 ?? EMAIL_DEFAULTS.disputeCc1,
        disputeCc2: dto.disputeCc2 ?? EMAIL_DEFAULTS.disputeCc2,
        disputeCc3: dto.disputeCc3 ?? EMAIL_DEFAULTS.disputeCc3,
        disputeSubject: dto.disputeSubject ?? EMAIL_DEFAULTS.disputeSubject,
        disputeBody: dto.disputeBody ?? EMAIL_DEFAULTS.disputeBody,
      },
    });
  }

  /** Raw settings (with real password) for the email transporter. */
  async getEmailSettingsRaw() {
    const settings = await this.prisma.emailSettings.findFirst();
    return settings ?? EMAIL_DEFAULTS;
  }

  // ──────────────────────────────────────────────
  // WEBSITE SETTINGS (B2C CMS)
  // ──────────────────────────────────────────────

  async getWebsiteSettings() {
    const settings = await this.prisma.websiteSettings.findFirst();
    if (!settings) {
      return WEBSITE_DEFAULTS;
    }
    return settings;
  }

  async updateWebsiteSettings(dto: UpdateWebsiteSettingsDto) {
    const existing = await this.prisma.websiteSettings.findFirst();

    const data: Record<string, unknown> = {};
    if (dto.siteName !== undefined) data.siteName = dto.siteName;
    if (dto.fontFamily !== undefined) data.fontFamily = dto.fontFamily;
    if (dto.primaryColor !== undefined) data.primaryColor = dto.primaryColor;
    if (dto.accentColor !== undefined) data.accentColor = dto.accentColor;
    if (dto.heroGradientFrom !== undefined) data.heroGradientFrom = dto.heroGradientFrom;
    if (dto.heroGradientTo !== undefined) data.heroGradientTo = dto.heroGradientTo;
    if (dto.navBgColor !== undefined) data.navBgColor = dto.navBgColor;
    if (dto.footerBgColor !== undefined) data.footerBgColor = dto.footerBgColor;
    if (dto.headerPreset !== undefined) data.headerPreset = dto.headerPreset;
    if (dto.footerPreset !== undefined) data.footerPreset = dto.footerPreset;
    if (dto.heroTitle !== undefined) data.heroTitle = dto.heroTitle;
    if (dto.heroSubtitle !== undefined) data.heroSubtitle = dto.heroSubtitle;
    if (dto.heroCta1Text !== undefined) data.heroCta1Text = dto.heroCta1Text;
    if (dto.heroCta2Text !== undefined) data.heroCta2Text = dto.heroCta2Text;
    if (dto.heroImageUrl !== undefined) data.heroImageUrl = dto.heroImageUrl || null;
    if (dto.featuresEnabled !== undefined) data.featuresEnabled = dto.featuresEnabled;
    if (dto.featuresTitle !== undefined) data.featuresTitle = dto.featuresTitle;
    if (dto.featuresJson !== undefined) data.featuresJson = dto.featuresJson;
    if (dto.contactEmail !== undefined) data.contactEmail = dto.contactEmail || null;
    if (dto.contactPhone !== undefined) data.contactPhone = dto.contactPhone || null;
    if (dto.contactWhatsapp !== undefined) data.contactWhatsapp = dto.contactWhatsapp || null;
    if (dto.socialFacebook !== undefined) data.socialFacebook = dto.socialFacebook || null;
    if (dto.socialInstagram !== undefined) data.socialInstagram = dto.socialInstagram || null;
    if (dto.socialTwitter !== undefined) data.socialTwitter = dto.socialTwitter || null;
    if (dto.opsNotificationEmails !== undefined) data.opsNotificationEmails = dto.opsNotificationEmails || null;
    if (dto.financeNotificationEmails !== undefined) data.financeNotificationEmails = dto.financeNotificationEmails || null;
    if (dto.bankPaymentEnabled !== undefined) data.bankPaymentEnabled = dto.bankPaymentEnabled;
    if (dto.bankPaymentMessage !== undefined) data.bankPaymentMessage = dto.bankPaymentMessage;
    if (dto.onlinePaymentEnabled !== undefined) data.onlinePaymentEnabled = dto.onlinePaymentEnabled;
    if (dto.cashOnArrivalEnabled !== undefined) data.cashOnArrivalEnabled = dto.cashOnArrivalEnabled;
    if (dto.enableTwoWayTab !== undefined) data.enableTwoWayTab = dto.enableTwoWayTab;
    if (dto.enableCityToCityTab !== undefined) data.enableCityToCityTab = dto.enableCityToCityTab;
    if (dto.enableMapSelector !== undefined) data.enableMapSelector = dto.enableMapSelector;
    if (dto.enableAiMode !== undefined) data.enableAiMode = dto.enableAiMode;
    if (dto.bookingTabsOrder !== undefined) data.bookingTabsOrder = dto.bookingTabsOrder;
    if (dto.metaTitle !== undefined) data.metaTitle = dto.metaTitle || null;
    if (dto.metaDescription !== undefined) data.metaDescription = dto.metaDescription || null;
    if (dto.navLinksJson !== undefined) data.navLinksJson = dto.navLinksJson;

    if (existing) {
      return this.prisma.websiteSettings.update({
        where: { id: existing.id },
        data,
      });
    }

    return this.prisma.websiteSettings.create({
      data: {
        siteName: dto.siteName ?? WEBSITE_DEFAULTS.siteName,
        fontFamily: dto.fontFamily ?? WEBSITE_DEFAULTS.fontFamily,
        primaryColor: dto.primaryColor ?? WEBSITE_DEFAULTS.primaryColor,
        accentColor: dto.accentColor ?? WEBSITE_DEFAULTS.accentColor,
        heroGradientFrom: dto.heroGradientFrom ?? WEBSITE_DEFAULTS.heroGradientFrom,
        heroGradientTo: dto.heroGradientTo ?? WEBSITE_DEFAULTS.heroGradientTo,
        navBgColor: dto.navBgColor ?? WEBSITE_DEFAULTS.navBgColor,
        footerBgColor: dto.footerBgColor ?? WEBSITE_DEFAULTS.footerBgColor,
        headerPreset: dto.headerPreset ?? WEBSITE_DEFAULTS.headerPreset,
        footerPreset: dto.footerPreset ?? WEBSITE_DEFAULTS.footerPreset,
        heroTitle: dto.heroTitle ?? WEBSITE_DEFAULTS.heroTitle,
        heroSubtitle: dto.heroSubtitle ?? WEBSITE_DEFAULTS.heroSubtitle,
        heroCta1Text: dto.heroCta1Text ?? WEBSITE_DEFAULTS.heroCta1Text,
        heroCta2Text: dto.heroCta2Text ?? WEBSITE_DEFAULTS.heroCta2Text,
        heroImageUrl: dto.heroImageUrl ?? WEBSITE_DEFAULTS.heroImageUrl,
        featuresEnabled: dto.featuresEnabled ?? WEBSITE_DEFAULTS.featuresEnabled,
        featuresTitle: dto.featuresTitle ?? WEBSITE_DEFAULTS.featuresTitle,
        featuresJson: dto.featuresJson ?? WEBSITE_DEFAULTS.featuresJson,
        contactEmail: dto.contactEmail ?? WEBSITE_DEFAULTS.contactEmail,
        contactPhone: dto.contactPhone ?? WEBSITE_DEFAULTS.contactPhone,
        contactWhatsapp: dto.contactWhatsapp ?? WEBSITE_DEFAULTS.contactWhatsapp,
        socialFacebook: dto.socialFacebook ?? WEBSITE_DEFAULTS.socialFacebook,
        socialInstagram: dto.socialInstagram ?? WEBSITE_DEFAULTS.socialInstagram,
        socialTwitter: dto.socialTwitter ?? WEBSITE_DEFAULTS.socialTwitter,
        opsNotificationEmails: dto.opsNotificationEmails ?? WEBSITE_DEFAULTS.opsNotificationEmails,
        financeNotificationEmails: dto.financeNotificationEmails ?? WEBSITE_DEFAULTS.financeNotificationEmails,
        bankPaymentEnabled: dto.bankPaymentEnabled ?? WEBSITE_DEFAULTS.bankPaymentEnabled,
        bankPaymentMessage: dto.bankPaymentMessage ?? WEBSITE_DEFAULTS.bankPaymentMessage,
        onlinePaymentEnabled: dto.onlinePaymentEnabled ?? WEBSITE_DEFAULTS.onlinePaymentEnabled,
        cashOnArrivalEnabled: dto.cashOnArrivalEnabled ?? WEBSITE_DEFAULTS.cashOnArrivalEnabled,
        enableTwoWayTab: dto.enableTwoWayTab ?? WEBSITE_DEFAULTS.enableTwoWayTab,
        enableCityToCityTab: dto.enableCityToCityTab ?? WEBSITE_DEFAULTS.enableCityToCityTab,
        enableMapSelector: dto.enableMapSelector ?? WEBSITE_DEFAULTS.enableMapSelector,
        enableAiMode: dto.enableAiMode ?? WEBSITE_DEFAULTS.enableAiMode,
        bookingTabsOrder: dto.bookingTabsOrder ?? WEBSITE_DEFAULTS.bookingTabsOrder,
        metaTitle: dto.metaTitle ?? WEBSITE_DEFAULTS.metaTitle,
        metaDescription: dto.metaDescription ?? WEBSITE_DEFAULTS.metaDescription,
        navLinksJson: dto.navLinksJson ?? WEBSITE_DEFAULTS.navLinksJson,
      },
    });
  }

  async updateSiteLogo(fileUrl: string) {
    const existing = await this.prisma.websiteSettings.findFirst();

    if (existing) {
      return this.prisma.websiteSettings.update({
        where: { id: existing.id },
        data: { siteLogoUrl: fileUrl },
      });
    }

    return this.prisma.websiteSettings.create({
      data: {
        siteName: WEBSITE_DEFAULTS.siteName,
        siteLogoUrl: fileUrl,
      },
    });
  }

  async updateSiteFavicon(fileUrl: string) {
    const existing = await this.prisma.websiteSettings.findFirst();

    if (existing) {
      return this.prisma.websiteSettings.update({
        where: { id: existing.id },
        data: { siteFaviconUrl: fileUrl },
      });
    }

    return this.prisma.websiteSettings.create({
      data: {
        siteName: WEBSITE_DEFAULTS.siteName,
        siteFaviconUrl: fileUrl,
      },
    });
  }

  async updateHeroImage(fileUrl: string) {
    const existing = await this.prisma.websiteSettings.findFirst();

    if (existing) {
      return this.prisma.websiteSettings.update({
        where: { id: existing.id },
        data: { heroImageUrl: fileUrl },
      });
    }

    return this.prisma.websiteSettings.create({
      data: {
        siteName: WEBSITE_DEFAULTS.siteName,
        heroImageUrl: fileUrl,
      },
    });
  }

  async updateInnerBgImage(fileUrl: string) {
    const existing = await this.prisma.systemSettings.findFirst();
    if (existing) {
      return this.prisma.systemSettings.update({ where: { id: existing.id }, data: { innerBgImageUrl: fileUrl } });
    }
    return this.prisma.systemSettings.create({ data: { innerBgImageUrl: fileUrl } });
  }

  async updateLoginBgImage(fileUrl: string) {
    const existing = await this.prisma.systemSettings.findFirst();
    if (existing) {
      return this.prisma.systemSettings.update({ where: { id: existing.id }, data: { loginBgImageUrl: fileUrl } });
    }
    return this.prisma.systemSettings.create({ data: { loginBgImageUrl: fileUrl } });
  }

  async updateLoginLogoImage(fileUrl: string) {
    const existing = await this.prisma.systemSettings.findFirst();
    if (existing) {
      return this.prisma.systemSettings.update({ where: { id: existing.id }, data: { loginLogoUrl: fileUrl } });
    }
    return this.prisma.systemSettings.create({ data: { loginLogoUrl: fileUrl } });
  }

  // ──────────────────────────────────────────────
  // GOOGLE DRIVE SETTINGS
  // ──────────────────────────────────────────────

  async getGoogleDriveSettings() {
    const row = await this.prisma.googleDriveSettings.findFirst();
    return {
      enabled: row?.enabled ?? false,
      oauthClientId: row?.oauthClientId ?? null,
      // mask secrets — never expose raw values
      oauthClientSecret: row?.oauthClientSecret ? '••••••••' : null,
      oauthRefreshToken: row?.oauthRefreshToken ? '••••••••' : null,
      rootFolderId: row?.rootFolderId ?? null,
      isConnected: !!(row?.oauthRefreshToken),
    };
  }

  async disconnectGoogleDrive() {
    const existing = await this.prisma.googleDriveSettings.findFirst();
    if (!existing) return;
    await this.prisma.googleDriveSettings.update({
      where: { id: existing.id },
      data: { oauthRefreshToken: null },
    });
  }

  async updateGoogleDriveSettings(dto: UpdateGoogleDriveSettingsDto) {
    const existing = await this.prisma.googleDriveSettings.findFirst();
    const data: Record<string, unknown> = {};

    if (dto.enabled !== undefined) data.enabled = dto.enabled;
    if (dto.rootFolderId !== undefined) data.rootFolderId = dto.rootFolderId || null;
    if (dto.oauthClientId !== undefined) data.oauthClientId = dto.oauthClientId || null;

    // Only overwrite secret if a real value is submitted (not the masked placeholder)
    if (dto.oauthClientSecret !== undefined && dto.oauthClientSecret !== '••••••••') {
      data.oauthClientSecret = dto.oauthClientSecret || null;
      // Changing credentials invalidates any stored refresh token
      data.oauthRefreshToken = null;
    }

    if (existing) {
      return this.prisma.googleDriveSettings.update({ where: { id: existing.id }, data });
    }

    return this.prisma.googleDriveSettings.create({
      data: {
        enabled: dto.enabled ?? false,
        oauthClientId: dto.oauthClientId ?? null,
        oauthClientSecret: dto.oauthClientSecret ?? null,
        rootFolderId: dto.rootFolderId ?? null,
      },
    });
  }
}
