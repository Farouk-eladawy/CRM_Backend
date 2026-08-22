import { Module } from '@nestjs/common';
import { PaymentsController } from './payments.controller.js';
import { PaymentsService } from './payments.service.js';
import { StripeGateway } from './gateways/stripe.gateway.js';
import { EgyptBankGateway } from './gateways/egypt-bank.gateway.js';
import { DubaiBankGateway } from './gateways/dubai-bank.gateway.js';
import { GetPayInGateway } from './gateways/getpayin.gateway.js';
import { EmailModule } from '../email/email.module.js';
import { B2CModule } from '../b2c/b2c.module.js';

@Module({
  imports: [EmailModule, B2CModule],
  controllers: [PaymentsController],
  providers: [
    PaymentsService,
    StripeGateway,
    EgyptBankGateway,
    DubaiBankGateway,
    GetPayInGateway,
  ],
  exports: [PaymentsService],
})
export class PaymentsModule {}
