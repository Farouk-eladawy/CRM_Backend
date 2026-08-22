import { IsString } from 'class-validator';

export class AssignZoneDto {
  @IsString()
  zoneId!: string;
}
