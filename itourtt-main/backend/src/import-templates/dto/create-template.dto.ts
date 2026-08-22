import { IsNotEmpty, IsString, IsOptional, IsObject } from 'class-validator';

export class CreateTemplateDto {
  @IsNotEmpty()
  @IsString()
  serviceType!: string;

  @IsOptional()
  @IsObject()
  fieldMappings?: Record<string, string>;

  @IsOptional()
  @IsString()
  notes?: string;
}
