import { PartialType } from '@nestjs/mapped-types';
import { CreateAgentDto } from './create-agent.dto.js';

export class UpdateAgentDto extends PartialType(CreateAgentDto) {}
