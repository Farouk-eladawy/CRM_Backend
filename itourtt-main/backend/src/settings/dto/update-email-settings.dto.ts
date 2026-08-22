import { IsOptional, IsString, IsInt, IsBoolean, IsEmail, Min, Max } from 'class-validator';

export class UpdateEmailSettingsDto {
  @IsOptional()
  @IsString()
  smtpHost?: string;

  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(65535)
  smtpPort?: number;

  @IsOptional()
  @IsBoolean()
  smtpSecure?: boolean;

  @IsOptional()
  @IsString()
  smtpUser?: string;

  @IsOptional()
  @IsString()
  smtpPass?: string;

  @IsOptional()
  @IsString()
  fromAddress?: string;

  @IsOptional()
  @IsString()
  notifyDispatchEmail?: string;

  @IsOptional()
  @IsString()
  notifyTrafficEmail?: string;

  @IsOptional()
  @IsEmail()
  disputeTo?: string;

  @IsOptional()
  @IsEmail()
  disputeCc1?: string;

  @IsOptional()
  @IsEmail()
  disputeCc2?: string;

  @IsOptional()
  @IsEmail()
  disputeCc3?: string;

  @IsOptional()
  @IsString()
  disputeSubject?: string;

  @IsOptional()
  @IsString()
  disputeBody?: string;
}
