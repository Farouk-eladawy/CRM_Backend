import { IsOptional, IsDateString, IsIn, IsString } from 'class-validator';
import { PaginationDto } from '../../common/dto/pagination.dto.js';
import { ALL_SERVICE_TYPES } from '../../common/utils/service-type.util.js';

export class JobFilterDto extends PaginationDto {
  @IsOptional()
  @IsDateString()
  date?: string;

  @IsOptional()
  @IsIn(['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'])
  status?: 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';

  @IsOptional()
  @IsString()
  agentId?: string;

  @IsOptional()
  @IsIn(ALL_SERVICE_TYPES as unknown as string[])
  serviceType?: string;

  @IsOptional()
  @IsString()
  bookingChannel?: string;

  @IsOptional()
  @IsString()
  search?: string;
}
