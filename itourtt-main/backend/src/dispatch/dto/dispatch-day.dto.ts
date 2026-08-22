import { IsNotEmpty, IsDateString } from 'class-validator';

export class DispatchDayDto {
  @IsNotEmpty()
  @IsDateString()
  date!: string;
}
