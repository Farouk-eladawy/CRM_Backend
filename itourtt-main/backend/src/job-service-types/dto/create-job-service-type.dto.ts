import { IsString, IsNotEmpty, IsOptional, IsBoolean } from 'class-validator';

export class CreateJobServiceTypeDto {
  @IsString()
  @IsNotEmpty()
  name: string;

  @IsOptional()
  @IsString()
  fromZoneId?: string;

  @IsOptional()
  @IsString()
  toZoneId?: string;

  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}
