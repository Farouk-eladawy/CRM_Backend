import { IsString, IsNotEmpty, IsOptional, IsEmail, IsEnum, IsNumber, IsInt, Min } from 'class-validator';
import { Currency } from '../../../generated/prisma/enums.js';

export class CreateCustomerDto {
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

  @IsString()
  @IsOptional()
  contactPerson?: string;

  @IsEnum(Currency)
  @IsOptional()
  currency?: string;

  @IsNumber()
  @IsOptional()
  @Min(0)
  creditLimit?: number;

  @IsInt()
  @IsOptional()
  @Min(0)
  creditDays?: number;
}
