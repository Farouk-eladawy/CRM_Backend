import { IsEnum, IsOptional, IsInt, Min, Max } from 'class-validator';
import { InvoiceCycleType } from '../../../generated/prisma/enums.js';

export class UpdateInvoiceCycleDto {
  @IsEnum(InvoiceCycleType)
  cycleType!: string;

  @IsOptional()
  @IsInt()
  @Min(0)
  @Max(6)
  dayOfWeek?: number;

  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(31)
  dayOfMonth?: number;
}
