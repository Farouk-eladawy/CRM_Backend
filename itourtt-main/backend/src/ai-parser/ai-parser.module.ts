import { Module } from '@nestjs/common';
import { AiParserController } from './ai-parser.controller.js';
import { AiParserService } from './ai-parser.service.js';
import { ImportTemplatesModule } from '../import-templates/import-templates.module.js';

@Module({
  imports: [ImportTemplatesModule],
  controllers: [AiParserController],
  providers: [AiParserService],
})
export class AiParserModule {}
