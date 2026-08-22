import { IsOptional, IsString } from 'class-validator';

export class UpdateCompanySettingsDto {
  @IsOptional()
  @IsString()
  companyName?: string;

  @IsOptional()
  @IsString()
  reportHeaderHtml?: string;

  @IsOptional()
  @IsString()
  reportFooterHtml?: string;

  @IsOptional()
  @IsString()
  licenseKey?: string;

  @IsOptional()
  @IsString()
  systemNotificationEmail?: string;
}
