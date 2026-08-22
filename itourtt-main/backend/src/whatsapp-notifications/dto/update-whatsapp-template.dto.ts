import { IsBoolean, IsInt, IsOptional, IsString, Max, Min } from 'class-validator';

export class UpdateWhatsappTemplateDto {
  @IsOptional()
  @IsString()
  name?: string;

  @IsOptional()
  @IsBoolean()
  isEnabled?: boolean;

  @IsOptional()
  @IsString()
  templateBody?: string;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(30)
  daysBefore?: number | null;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(23)
  sendHour?: number | null;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(59)
  sendMinute?: number | null;
}
