import { IsString, IsNotEmpty, IsOptional, IsEmail, IsEnum } from 'class-validator';
import { Currency } from '../../../generated/prisma/enums.js';

export class CreateAgentDto {
  @IsString()
  @IsNotEmpty()
  legalName!: string;

  @IsString()
  @IsOptional()
  tradeName?: string;

  @IsString()
  @IsOptional()
  taxId?: string;

  @IsString()
  @IsOptional()
  address?: string;

  @IsString()
  @IsOptional()
  city?: string;

  @IsString()
  @IsOptional()
  country?: string;

  @IsString()
  @IsOptional()
  phone?: string;

  @IsEmail()
  @IsOptional()
  email?: string;

  @IsEmail()
  @IsOptional()
  disputeEmail?: string;

  @IsEnum(Currency)
  @IsOptional()
  currency?: string;

  @IsString()
  @IsOptional()
  refPattern?: string;

  @IsString()
  @IsOptional()
  refExample?: string;
}
