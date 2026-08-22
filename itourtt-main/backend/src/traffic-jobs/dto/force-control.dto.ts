import { IsOptional, IsIn } from 'class-validator';

const JOB_STATUSES = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'] as const;
const PORTAL_STATUSES = ['PENDING', 'IN_PROGRESS', 'IN_PLACE', 'COMPLETED', 'CANCELLED', 'NO_SHOW'] as const;

export class ForceControlDto {
  @IsOptional()
  @IsIn(JOB_STATUSES)
  jobStatus?: (typeof JOB_STATUSES)[number];

  @IsOptional()
  @IsIn(PORTAL_STATUSES)
  repStatus?: (typeof PORTAL_STATUSES)[number];

  @IsOptional()
  @IsIn(PORTAL_STATUSES)
  driverStatus?: (typeof PORTAL_STATUSES)[number];
}
