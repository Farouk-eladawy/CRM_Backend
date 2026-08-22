import { IsNumber, IsInt, Min } from 'class-validator';

export class UpdateCreditDto {
  @IsNumber({ maxDecimalPlaces: 2 })
  @Min(0)
  creditLimit!: number;

  @IsInt()
  @Min(0)
  creditDays!: number;
}
