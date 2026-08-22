import { Injectable, BadRequestException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Stripe from 'stripe';
import type {
  PaymentGateway,
  PaymentSessionResult,
  PaymentVerificationResult,
} from './gateway.interface.js';

@Injectable()
export class StripeGateway implements PaymentGateway {
  private stripe: Stripe | null = null;

  constructor(private readonly configService: ConfigService) {
    const secretKey = this.configService.get<string>('STRIPE_SECRET_KEY');
    if (secretKey) {
      this.stripe = new Stripe(secretKey, {
        apiVersion: '2024-12-18.acacia' as Stripe.LatestApiVersion,
      });
    }
  }

  private ensureConfigured(): Stripe {
    if (!this.stripe) {
      throw new BadRequestException(
        'Stripe is not configured. Set STRIPE_SECRET_KEY environment variable.',
      );
    }
    return this.stripe;
  }

  async createSession(
    bookingRef: string,
    amount: number,
    currency: string,
    returnUrl: string,
    cancelUrl: string,
  ): Promise<PaymentSessionResult> {
    const stripe = this.ensureConfigured();

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: currency.toLowerCase(),
            product_data: {
              name: `Transfer Booking ${bookingRef}`,
              description: `Payment for booking reference: ${bookingRef}`,
            },
            unit_amount: Math.round(amount * 100), // Stripe uses smallest currency unit
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: returnUrl,
      cancel_url: cancelUrl,
      metadata: {
        bookingRef,
      },
    });

    return {
      sessionId: session.id,
      checkoutUrl: session.url || '',
      gateway: 'STRIPE',
    };
  }

  async verifyPayment(sessionId: string): Promise<PaymentVerificationResult> {
    const stripe = this.ensureConfigured();

    const session = await stripe.checkout.sessions.retrieve(sessionId);

    return {
      success: session.payment_status === 'paid',
      transactionId: (session.payment_intent as string) || session.id,
      amount: (session.amount_total || 0) / 100,
      currency: (session.currency || 'usd').toUpperCase(),
    };
  }

  async refund(
    transactionId: string,
    amount: number,
  ): Promise<{ success: boolean; refundId: string }> {
    const stripe = this.ensureConfigured();

    const refund = await stripe.refunds.create({
      payment_intent: transactionId,
      amount: Math.round(amount * 100),
    });

    return {
      success: refund.status === 'succeeded',
      refundId: refund.id,
    };
  }
}
