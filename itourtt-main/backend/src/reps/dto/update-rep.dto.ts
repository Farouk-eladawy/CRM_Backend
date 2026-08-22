import { PartialType } from '@nestjs/mapped-types';
import { CreateRepDto } from './create-rep.dto.js';

export class UpdateRepDto extends PartialType(CreateRepDto) {}
