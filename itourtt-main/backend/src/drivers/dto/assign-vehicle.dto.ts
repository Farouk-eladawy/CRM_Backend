import { IsString, IsOptional, IsBoolean } from 'class-validator';

export class AssignVehicleDto {
  @IsString()
  vehicleId!: string;

  @IsOptional()
  @IsBoolean()
  isPrimary?: boolean;
}
