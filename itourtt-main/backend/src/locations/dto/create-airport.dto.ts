import { IsNotEmpty, IsString, MaxLength, IsOptional, IsNumber } from 'class-validator';

export class CreateAirportDto {
  @IsNotEmpty()
  @IsString()
  name!: string;

  @IsNotEmpty()
  @IsString()
  @MaxLength(10)
  code!: string;

  @IsNotEmpty()
  @IsString()
  countryId!: string;

  @IsOptional()
  @IsNumber()
  latitude?: number;

  @IsOptional()
  @IsNumber()
  longitude?: number;

  @IsOptional()
  @IsString()
  placeId?: string;
}
