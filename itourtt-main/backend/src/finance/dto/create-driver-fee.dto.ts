import {
  IsNotEmpty,
  IsNumber,
  IsPositive,
  IsOptional,
  IsString,
} from 'class-validator';

export class CreateDriverFeeDto {
  @IsString()
  @IsNotEmpty()
  trafficJobId!: string;

  @IsString()
  @IsNotEmpty()
  driverId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;

  @IsString()
  @IsOptional()
  currency?: string;

  @IsNumber()
  @IsOptional()
  exchangeRate?: number;

  @IsString()
  @IsOptional()
  notes?: string;
}
