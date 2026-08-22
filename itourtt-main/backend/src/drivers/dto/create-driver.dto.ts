import { IsString, IsNotEmpty, IsOptional, IsDateString } from 'class-validator';

export class CreateDriverDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsString()
  @IsNotEmpty()
  mobileNumber!: string;

  @IsString()
  @IsOptional()
  licenseNumber?: string;

  @IsDateString()
  @IsOptional()
  licenseExpiryDate?: string;
}
