import {
  IsString,
  IsArray,
  IsDateString,
  IsOptional,
  IsNumber,
  Min,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';

export class CustomerInvoiceJobDto {
  @IsString()
  trafficJobId!: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  transferPrice?: number;

  @IsOptional()
  @IsNumber()
  @Min(0)
  driverTip?: number;
}

export class GenerateCustomerInvoicesDto {
  @IsString()
  customerId!: string;

  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  trafficJobIds?: string[];

  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => CustomerInvoiceJobDto)
  jobs?: CustomerInvoiceJobDto[];

  @IsDateString()
  issueDate!: string;

  @IsOptional()
  @IsDateString()
  dueDate?: string;
}
