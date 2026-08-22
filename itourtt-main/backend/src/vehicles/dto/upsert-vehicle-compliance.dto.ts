import {
  IsOptional,
  IsBoolean,
  IsDateString,
  IsNumber,
  IsIn,
  Min,
} from 'class-validator';

export class UpsertVehicleComplianceDto {
  @IsOptional()
  @IsDateString()
  licenseExpiryDate?: string;

  @IsOptional()
  @IsBoolean()
  hasInsurance?: boolean;

  @IsOptional()
  @IsDateString()
  insuranceExpiryDate?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  annualPayment?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  annualPaymentCurrency?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  gpsSubscription?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  gpsSubscriptionCurrency?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  tourismSupportFund?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  tourismSupportFundCurrency?: string;

  @IsOptional()
  @IsNumber()
  @Min(0)
  registrationFees?: number;

  @IsOptional()
  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  registrationFeesCurrency?: string;

  @IsOptional()
  @IsDateString()
  temporaryPermitDate?: string;
}
