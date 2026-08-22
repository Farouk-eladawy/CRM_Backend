import { ValidateNested, IsArray, ArrayMinSize } from 'class-validator';
import { Type } from 'class-transformer';
import { CreateJobDto } from './create-job.dto.js';

export class BulkCreateJobsDto {
  @IsArray()
  @ArrayMinSize(1)
  @ValidateNested({ each: true })
  @Type(() => CreateJobDto)
  jobs!: CreateJobDto[];
}
