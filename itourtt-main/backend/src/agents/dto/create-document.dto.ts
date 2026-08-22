import { IsString, IsNotEmpty, IsOptional, IsEnum, IsDateString } from 'class-validator';
import { DocumentType } from '../../../generated/prisma/enums.js';

export class CreateDocumentDto {
  @IsEnum(DocumentType)
  documentType!: string;

  @IsString()
  @IsNotEmpty()
  fileUrl!: string;

  @IsString()
  @IsNotEmpty()
  fileName!: string;

  @IsDateString()
  @IsOptional()
  expiresAt?: string;
}
