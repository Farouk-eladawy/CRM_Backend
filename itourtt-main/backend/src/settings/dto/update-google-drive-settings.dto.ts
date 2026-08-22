import { IsBoolean, IsOptional, IsString } from 'class-validator';

export class UpdateGoogleDriveSettingsDto {
  @IsOptional()
  @IsBoolean()
  enabled?: boolean;

  @IsOptional()
  @IsString()
  oauthClientId?: string;

  @IsOptional()
  @IsString()
  oauthClientSecret?: string;

  @IsOptional()
  @IsString()
  rootFolderId?: string;
}

export class GoogleDriveAuthUrlDto {
  @IsString()
  redirectUri!: string;
}

export class GoogleDriveExchangeCodeDto {
  @IsString()
  code!: string;

  @IsString()
  redirectUri!: string;
}
