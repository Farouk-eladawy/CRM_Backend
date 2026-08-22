import { IsNumber, IsIn, IsDateString, Min } from 'class-validator';

export class CreateDepositPaymentDto {
  @IsNumber()
  @Min(0)
  amount: number;

  @IsIn(['EGP', 'USD', 'EUR', 'GBP', 'SAR'])
  currency: string;

  @IsDateString()
  paidAt: string;
}
