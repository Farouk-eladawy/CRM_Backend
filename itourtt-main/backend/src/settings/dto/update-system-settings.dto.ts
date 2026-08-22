import { IsIn, IsOptional, IsString, Matches } from 'class-validator';

export class UpdateSystemSettingsDto {
  @IsOptional()
  @IsString()
  @IsIn(['light', 'dark'])
  theme?: string;

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
  @Matches(/^#[0-9a-fA-F]{6}$/, { message: 'sidebarColor must be a valid hex color (e.g. #41004c)' })
  sidebarColor?: string;

  @IsOptional()
  @IsString()
  fontFamily?: string;

  @IsOptional()
  @IsString()
  language?: string;

  @IsOptional()
  @IsString()
  googleMapsApiKey?: string;
}
