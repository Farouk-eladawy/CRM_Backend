import { IsOptional, IsString, IsBoolean, Matches } from 'class-validator';

export class UpdateWebsiteSettingsDto {
  // ── Site Identity ──
  @IsOptional()
  @IsString()
  siteName?: string;

  // ── Typography ──
  @IsOptional()
  @IsString()
  fontFamily?: string;

  // ── Color Theme ──
  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'primaryColor must be a valid hex color (e.g. #3b82f6)' })
  primaryColor?: string;

  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'accentColor must be a valid hex color (e.g. #8b5cf6)' })
  accentColor?: string;

  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'heroGradientFrom must be a valid hex color' })
  heroGradientFrom?: string;

  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'heroGradientTo must be a valid hex color' })
  heroGradientTo?: string;

  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'navBgColor must be a valid hex color' })
  navBgColor?: string;

  @IsOptional()
  @IsString()
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'footerBgColor must be a valid hex color' })
  footerBgColor?: string;

  // ── Header/Footer Presets ──
  @IsOptional()
  @IsString()
  headerPreset?: string;

  @IsOptional()
  @IsString()
  footerPreset?: string;

  // ── Hero Section Content ──
  @IsOptional()
  @IsString()
  heroTitle?: string;

  @IsOptional()
  @IsString()
  heroSubtitle?: string;

  @IsOptional()
  @IsString()
  heroCta1Text?: string;

  @IsOptional()
  @IsString()
  heroCta2Text?: string;

  @IsOptional()
  @IsString()
  heroImageUrl?: string;

  // ── Features Section ──
  @IsOptional()
  @IsBoolean()
  featuresEnabled?: boolean;

  @IsOptional()
  @IsString()
  featuresTitle?: string;

  @IsOptional()
  featuresJson?: any;

  // ── Contact Info ──
  @IsOptional()
  @IsString()
  contactEmail?: string;

  @IsOptional()
  @IsString()
  contactPhone?: string;

  @IsOptional()
  @IsString()
  contactWhatsapp?: string;

  @IsOptional()
  @IsString()
  socialFacebook?: string;

  @IsOptional()
  @IsString()
  socialInstagram?: string;

  @IsOptional()
  @IsString()
  socialTwitter?: string;

  // ── Internal Booking Notifications (comma-separated recipient lists) ──
  @IsOptional()
  @IsString()
  opsNotificationEmails?: string;

  @IsOptional()
  @IsString()
  financeNotificationEmails?: string;

  // ── Bank Payment ──
  @IsOptional()
  @IsBoolean()
  bankPaymentEnabled?: boolean;

  @IsOptional()
  @IsString()
  bankPaymentMessage?: string;

  // ── Payment Method Master Switches ──
  @IsOptional()
  @IsBoolean()
  onlinePaymentEnabled?: boolean;

  @IsOptional()
  @IsBoolean()
  cashOnArrivalEnabled?: boolean;

  // ── Booking Widget Master Switches ──
  @IsOptional()
  @IsBoolean()
  enableTwoWayTab?: boolean;

  @IsOptional()
  @IsBoolean()
  enableCityToCityTab?: boolean;

  @IsOptional()
  @IsBoolean()
  enableMapSelector?: boolean;

  @IsOptional()
  @IsBoolean()
  enableAiMode?: boolean;

  @IsOptional()
  @IsString()
  bookingTabsOrder?: string;

  // ── SEO ──
  @IsOptional()
  @IsString()
  metaTitle?: string;

  @IsOptional()
  @IsString()
  metaDescription?: string;

  // ── Menu Links ──
  @IsOptional()
  navLinksJson?: any;
}
