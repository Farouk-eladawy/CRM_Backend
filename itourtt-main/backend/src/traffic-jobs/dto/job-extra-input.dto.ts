import {
  IsString,
  IsNotEmpty,
  IsOptional,
  IsInt,
  IsNumber,
  Min,
  IsIn,
} from 'class-validator';

const CURRENCIES = ['EGP', 'USD', 'EUR', 'GBP', 'SAR'];

// A single managed extra attached to a traffic job. extraId links the catalog item;
// name/unitAmount/currency are snapshots (operator-overridable for manual entry).
export class JobExtraInputDto {
  @IsOptional()
  @IsString()
  extraId?: string;

  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsInt()
  @Min(1)
  qty!: number;

  @IsNumber()
  @Min(0)
  unitAmount!: number;

  @IsIn(CURRENCIES)
  currency!: string;

  @IsOptional()
  @IsIn(['B2C', 'MANUAL'])
  source?: 'B2C' | 'MANUAL';
}
