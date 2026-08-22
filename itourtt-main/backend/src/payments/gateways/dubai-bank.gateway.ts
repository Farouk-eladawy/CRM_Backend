import { Injectable, NotImplementedException } from '@nestjs/common';
import type {
  PaymentGateway,
  PaymentSessionResult,
  PaymentVerificationResult,
} from './gateway.interface.js';

@Injectable()
export class DubaiBankGateway implements PaymentGateway {
  async createSession(
    _bookingRef: string,
    _amount: number,
    _currency: string,
    _returnUrl: string,
    _cancelUrl: string,
  ): Promise<PaymentSessionResult> {
    throw new NotImplementedException(
      'Dubai bank gateway not yet configured. Contact administrator.',
    );
  }

  async verifyPayment(_sessionId: string): Promise<PaymentVerificationResult> {
    throw new NotImplementedException(
      'Dubai bank gateway not yet configured. Contact administrator.',
    );
  }

  async refund(
    _transactionId: string,
    _amount: number,
  ): Promise<{ success: boolean; refundId: string }> {
    throw new NotImplementedException(
      'Dubai bank gateway not yet configured. Contact administrator.',
    );
  }
}
