import {
  IsArray,
  ValidateNested,
  IsString,
  IsNotEmpty,
  IsNumber,
  IsPositive,
  IsInt,
  Min,
  Max,
  IsOptional,
} from 'class-validator';
import { Type } from 'class-transformer';

export class UpdateInvoiceLineItemDto {
  @IsString()
  @IsOptional()
  id?: string;

  @IsString()
  @IsOptional()
  trafficJobId?: string;

  @IsString()
  @IsNotEmpty()
  description!: string;

  @IsInt()
  @Min(1)
  quantity!: number;

  @IsNumber()
  @IsPositive()
  unitPrice!: number;

  @IsNumber()
  @Min(0)
  @Max(100)
  taxRate!: number;
}

export class UpdateInvoiceLinesDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => UpdateInvoiceLineItemDto)
  lines!: UpdateInvoiceLineItemDto[];
}
