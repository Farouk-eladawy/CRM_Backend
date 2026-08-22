import { IsBoolean, IsOptional, IsString } from 'class-validator';

export class UpdateWhatsappSettingsDto {
  @IsOptional()
  @IsBoolean()
  isEnabled?: boolean;

  @IsOptional()
  @IsString()
  twilioAccountSid?: string;

  @IsOptional()
  @IsString()
  twilioAuthToken?: string;

  @IsOptional()
  @IsString()
  whatsappFrom?: string;

  @IsOptional()
  @IsString()
  mediaUrl?: string;
}
