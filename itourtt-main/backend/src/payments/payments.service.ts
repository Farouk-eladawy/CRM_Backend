import {
  Injectable,
  NotFoundException,
  BadRequestException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Stripe from 'stripe';
import { PrismaService } from '../prisma/prisma.service.js';
import { EmailService } from '../email/email.service.js';
import { B2CInvoiceService } from '../b2c/b2c-invoice.service.js';
import { StripeGateway } from './gateways/stripe.gateway.js';
import { EgyptBankGateway } from './gateways/egypt-bank.gateway.js';
import { DubaiBankGateway } from './gateways/dubai-bank.gateway.js';
import { GetPayInGateway } from './gateways/getpayin.gateway.js';
import type { GetPayInCallback } from './gateways/getpayin.gateway.js';
import type { PaymentGateway } from './gateways/gateway.interface.js';
import {
  B2CPaymentGateway,
  B2CPaymentStatus,
} from '../../generated/prisma/enums.js';

@Injectable()
export class PaymentsService {
  private readonly logger = new Logger(PaymentsService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
    private readonly emailService: EmailService,
    private readonly b2cInvoiceService: B2CInvoiceService,
    private readonly stripeGateway: StripeGateway,
    private readonly egyptBankGateway: EgyptBankGateway,
    private readonly dubaiBankGateway: DubaiBankGateway,
    private readonly getPayInGateway: GetPayInGateway,
  ) {}

  private getGateway(gateway: string): PaymentGateway {
    switch (gateway) {
      case 'STRIPE':
        return this.stripeGateway;
      case 'EGYPT_BANK':
        return this.egyptBankGateway;
      case 'DUBAI_BANK':
        return this.dubaiBankGateway;
      case 'GETPAYIN':
        return this.getPayInGateway;
      default:
        throw new BadRequestException(`Unsupported payment gateway: ${gateway}`);
    }
  }

  /**
   * Ensure a B2C invoice exists for a paid booking and return it as a mail
   * attachment. Idempotent (safe on webhook re-delivery). Never throws — a
   * failure here must not block the receipt email.
   */
  private async buildInvoiceAttachment(
    bookingId: string,
  ): Promise<Array<{ filename: string; content: Buffer }> | undefined> {
    try {
      const invoice = await this.b2cInvoiceService.ensureForBooking(bookingId);
      const { buffer, filename } = await this.b2cInvoiceService.generatePdf(invoice.id);
      return [{ filename, content: buffer }];
    } catch (err) {
      this.logger.error(
        `Failed to build invoice for booking ${bookingId}: ${(err as Error).message}`,
      );
      return undefined;
    }
  }

  async createPaymentSession(
    bookingRef: string,
    gateway: string,
    returnUrl: string,
    cancelUrl: string,
  ) {
    // Find the guest booking
    const booking = await this.prisma.guestBooking.findUnique({
      where: { bookingRef },
      include: { fromZone: true, toZone: true, vehicleType: true },
    });

    if (!booking) {
      throw new NotFoundException(
        `Booking with reference "${bookingRef}" not found`,
      );
    }

    if (booking.paymentStatus === B2CPaymentStatus.PAID as B2CPaymentStatus) {
      throw new BadRequestException('This booking has already been paid');
    }

    const paymentGateway = this.getGateway(gateway);

    // Split the single guest name into first/last for gateways that need it.
    const nameParts = (booking.guestName || '').trim().split(/\s+/);
    const firstName = nameParts.shift() || 'Guest';
    const lastName = nameParts.join(' ') || firstName;

    // Booking summary rows shown on the hosted checkout page (Cairo time).
    const fmtDate = (d: Date) =>
      new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Africa/Cairo',
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(d);
    const fmtTime = (d: Date) =>
      new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Africa/Cairo',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(d);

    const orderDetails: Array<{ label: string; value: string }> = [
      { label: 'Booking', value: bookingRef },
      { label: 'Guest', value: booking.guestName ?? '' },
      {
        label: 'Service',
        value:
          { ARR: 'Arrival', DEP: 'Departure', CITY: 'City Tour' }[
            booking.serviceType as string
          ] ?? booking.serviceType,
      },
      {
        label: 'Route',
        value: `${booking.fromZone?.name ?? ''} → ${booking.toZone?.name ?? ''}`,
      },
      { label: 'Date', value: fmtDate(booking.jobDate) },
      { label: 'Pickup', value: booking.pickupTime ? fmtTime(booking.pickupTime) : '' },
      { label: 'Vehicle', value: booking.vehicleType?.name ?? '' },
      { label: 'Passengers', value: String(booking.paxCount) },
      { label: 'Flight', value: booking.flightNo ?? '' },
    ];

    // Create the payment session with the gateway
    const session = await paymentGateway.createSession(
      bookingRef,
      Number(booking.total),
      booking.currency,
      returnUrl,
      cancelUrl,
      {
        firstName,
        lastName,
        email: booking.guestEmail,
        orderTitle: `Transfer Booking ${bookingRef}`,
        country: booking.guestCountry ?? undefined,
        orderDetails,
      },
    );

    // Create a PaymentTransaction record with status PENDING (INITIATED)
    await this.prisma.paymentTransaction.create({
      data: {
        guestBookingId: booking.id,
        gateway: gateway as B2CPaymentGateway,
        gatewayTransactionId: session.sessionId,
        amount: booking.total,
        currency: booking.currency,
        status: B2CPaymentStatus.PENDING as B2CPaymentStatus,
        rawResponse: { sessionId: session.sessionId, checkoutUrl: session.checkoutUrl },
      },
    });

    return {
      checkoutUrl: session.checkoutUrl,
      sessionId: session.sessionId,
      gateway: session.gateway,
    };
  }

  async handleStripeWebhook(rawBody: Buffer, signature: string) {
    const webhookSecret = this.configService.get<string>('STRIPE_WEBHOOK_SECRET');
    if (!webhookSecret) {
      throw new BadRequestException('Stripe webhook secret is not configured');
    }

    const stripeSecretKey = this.configService.get<string>('STRIPE_SECRET_KEY');
    if (!stripeSecretKey) {
      throw new BadRequestException('Stripe is not configured');
    }

    const stripe = new Stripe(stripeSecretKey, {
      apiVersion: '2024-12-18.acacia' as Stripe.LatestApiVersion,
    });

    let event: Stripe.Event;
    try {
      event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
    } catch (err) {
      this.logger.error(`Stripe webhook signature verification failed: ${err}`);
      throw new BadRequestException('Invalid webhook signature');
    }

    if (event.type === 'checkout.session.completed') {
      const session = event.data.object as Stripe.Checkout.Session;
      const sessionId = session.id;
      const bookingRef = session.metadata?.bookingRef;

      if (!bookingRef) {
        this.logger.warn(`Stripe webhook: no bookingRef in session metadata for ${sessionId}`);
        return { received: true };
      }

      // Find the payment transaction by gatewayTransactionId
      const transaction = await this.prisma.paymentTransaction.findFirst({
        where: { gatewayTransactionId: sessionId },
      });

      if (transaction) {
        // Update transaction status
        await this.prisma.paymentTransaction.update({
          where: { id: transaction.id },
          data: {
            status: B2CPaymentStatus.PAID as B2CPaymentStatus,
            rawResponse: JSON.parse(JSON.stringify(session)),
          },
        });

        // Update GuestBooking payment status
        const updatedBooking = await this.prisma.guestBooking.update({
          where: { bookingRef },
          data: {
            paymentStatus: B2CPaymentStatus.PAID as B2CPaymentStatus,
            paymentGateway: B2CPaymentGateway.STRIPE as B2CPaymentGateway,
            paymentReference: (session.payment_intent as string) || sessionId,
          },
        });
        // Mirror to the return leg of a 2-way booking (paid once, combined).
        if (updatedBooking.groupRef) {
          await this.prisma.guestBooking.updateMany({
            where: { groupRef: updatedBooking.groupRef, id: { not: updatedBooking.id } },
            data: { paymentStatus: B2CPaymentStatus.PAID as B2CPaymentStatus },
          });
        }

        this.logger.log(`Payment completed for booking ${bookingRef}, session ${sessionId}`);

        // Send payment receipt email (fire-and-forget)
        const paidBooking = await this.prisma.guestBooking.findUnique({
          where: { bookingRef },
        });
        if (paidBooking) {
          const invoiceAttachment = await this.buildInvoiceAttachment(paidBooking.id);
          this.emailService
            .sendPaymentReceipt({
              bookingRef,
              guestName: paidBooking.guestName,
              guestEmail: paidBooking.guestEmail,
              amount: Number(paidBooking.total),
              currency: paidBooking.currency,
              gateway: 'Stripe',
              transactionId: (session.payment_intent as string) || sessionId,
              paidAt: new Date().toISOString(),
            }, invoiceAttachment)
            .catch((err) =>
              this.logger.error(`Failed to send payment receipt email: ${err.message}`),
            );

          // Internal finance notification (recipients configured in admin CMS).
          this.emailService
            .notifyFinancePayment({
              bookingRef,
              guestName: paidBooking.guestName,
              guestEmail: paidBooking.guestEmail,
              amount: Number(paidBooking.total),
              currency: paidBooking.currency,
              gateway: 'Stripe',
              transactionId: (session.payment_intent as string) || sessionId,
              paidAt: new Date().toISOString(),
              paymentMethod: paidBooking.paymentMethod,
            })
            .catch((err) =>
              this.logger.error(`Failed to send finance payment notification: ${err.message}`),
            );
        }
      } else {
        this.logger.warn(`No payment transaction found for session ${sessionId}`);
      }
    }

    return { received: true };
  }

  /**
   * Process a GetPayIn callback (shared by the server-to-server webhook and the
   * browser redirect). Verifies the HMAC signature, then marks the matching
   * booking/transaction PAID or FAILED. Idempotent: re-delivery of an already
   * PAID transaction is a no-op. Returns the resolved booking ref + paid flag
   * so the redirect handler knows where to send the customer.
   */
  async processGetPayInCallback(
    payload: GetPayInCallback,
  ): Promise<{ bookingRef: string | null; paid: boolean }> {
    const valid = this.getPayInGateway.verifyCallback(payload);
    if (!valid) {
      throw new BadRequestException('Invalid GetPayIn signature');
    }

    const invoiceId = String(payload.invoice_id ?? '');
    const paid =
      payload.success === true ||
      payload.success === 'true' ||
      String(payload.invoice_status).toUpperCase() === 'PAID';

    const transaction = await this.prisma.paymentTransaction.findFirst({
      where: { gatewayTransactionId: invoiceId, gateway: B2CPaymentGateway.GETPAYIN },
      orderBy: { createdAt: 'desc' },
    });

    if (!transaction) {
      this.logger.warn(`GetPayIn callback: no transaction for invoice ${invoiceId}`);
      return { bookingRef: null, paid };
    }

    const booking = await this.prisma.guestBooking.findUnique({
      where: { id: transaction.guestBookingId },
    });
    if (!booking) {
      return { bookingRef: null, paid };
    }

    // Idempotency — ignore repeat deliveries once already settled.
    if (booking.paymentStatus === (B2CPaymentStatus.PAID as B2CPaymentStatus)) {
      return { bookingRef: booking.bookingRef, paid: true };
    }

    const newStatus = paid
      ? (B2CPaymentStatus.PAID as B2CPaymentStatus)
      : (B2CPaymentStatus.FAILED as B2CPaymentStatus);

    await this.prisma.paymentTransaction.update({
      where: { id: transaction.id },
      data: {
        status: newStatus,
        rawResponse: JSON.parse(JSON.stringify(payload)),
      },
    });

    await this.prisma.guestBooking.update({
      where: { id: booking.id },
      data: {
        paymentStatus: newStatus,
        paymentGateway: B2CPaymentGateway.GETPAYIN as B2CPaymentGateway,
        paymentReference: invoiceId,
      },
    });

    // 2-way bookings are paid once (combined amount on the outbound leg). Mirror
    // the settled status to the return leg so it isn't left looking unpaid.
    if (booking.groupRef) {
      await this.prisma.guestBooking.updateMany({
        where: { groupRef: booking.groupRef, id: { not: booking.id } },
        data: { paymentStatus: newStatus, paymentReference: invoiceId },
      });
    }

    this.logger.log(
      `GetPayIn callback: booking ${booking.bookingRef} → ${newStatus} (invoice ${invoiceId})`,
    );

    // Failed online payment → fall back to cash on arrival: flag the already-
    // created traffic job for collection and tell the guest.
    if (!paid && booking.trafficJobId) {
      await this.prisma.trafficJob.update({
        where: { id: booking.trafficJobId },
        data: {
          collectionRequired: true,
          collectionAmount: booking.total,
          collectionCurrency: booking.currency,
        },
      });
      this.logger.log(
        `GetPayIn payment failed for ${booking.bookingRef} → traffic job ${booking.trafficJobId} flagged collect-cash`,
      );
      this.emailService
        .sendOnlinePaymentFailed({
          bookingRef: booking.bookingRef,
          guestName: booking.guestName,
          guestEmail: booking.guestEmail,
          amount: Number(booking.total),
          currency: booking.currency,
        })
        .catch((err) =>
          this.logger.error(`Failed to send payment-failed email: ${err.message}`),
        );
    }

    if (paid) {
      const invoiceAttachment = await this.buildInvoiceAttachment(booking.id);
      this.emailService
        .sendPaymentReceipt({
          bookingRef: booking.bookingRef,
          guestName: booking.guestName,
          guestEmail: booking.guestEmail,
          amount: Number(booking.total),
          currency: booking.currency,
          gateway: 'GetPayIn',
          transactionId: invoiceId,
          paidAt: new Date().toISOString(),
        }, invoiceAttachment)
        .catch((err) =>
          this.logger.error(`Failed to send payment receipt email: ${err.message}`),
        );

      // Internal finance notification (recipients configured in admin CMS).
      this.emailService
        .notifyFinancePayment({
          bookingRef: booking.bookingRef,
          guestName: booking.guestName,
          guestEmail: booking.guestEmail,
          amount: Number(booking.total),
          currency: booking.currency,
          gateway: 'GetPayIn',
          transactionId: invoiceId,
          paidAt: new Date().toISOString(),
          paymentMethod: booking.paymentMethod,
        })
        .catch((err) =>
          this.logger.error(`Failed to send finance payment notification: ${err.message}`),
        );
    }

    return { bookingRef: booking.bookingRef, paid };
  }

  async verifyPaymentStatus(bookingRef: string) {
    const booking = await this.prisma.guestBooking.findUnique({
      where: { bookingRef },
      include: {
        paymentTransactions: {
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
    });

    if (!booking) {
      throw new NotFoundException(
        `Booking with reference "${bookingRef}" not found`,
      );
    }

    const latestTransaction = booking.paymentTransactions[0] || null;

    return {
      bookingRef: booking.bookingRef,
      paymentStatus: booking.paymentStatus,
      paymentMethod: booking.paymentMethod,
      paymentGateway: booking.paymentGateway,
      paymentReference: booking.paymentReference,
      total: Number(booking.total),
      currency: booking.currency,
      latestTransaction: latestTransaction
        ? {
            id: latestTransaction.id,
            gateway: latestTransaction.gateway,
            status: latestTransaction.status,
            amount: Number(latestTransaction.amount),
            currency: latestTransaction.currency,
            createdAt: latestTransaction.createdAt,
          }
        : null,
    };
  }

  async refundPayment(bookingRef: string) {
    const booking = await this.prisma.guestBooking.findUnique({
      where: { bookingRef },
      include: {
        paymentTransactions: {
          where: { status: B2CPaymentStatus.PAID as B2CPaymentStatus },
          orderBy: { createdAt: 'desc' },
          take: 1,
        },
      },
    });

    if (!booking) {
      throw new NotFoundException(
        `Booking with reference "${bookingRef}" not found`,
      );
    }

    if (booking.paymentStatus !== (B2CPaymentStatus.PAID as B2CPaymentStatus)) {
      throw new BadRequestException(
        'Cannot refund a booking that has not been paid',
      );
    }

    const successfulTransaction = booking.paymentTransactions[0];
    if (!successfulTransaction) {
      throw new NotFoundException(
        'No successful payment transaction found for this booking',
      );
    }

    const gateway = this.getGateway(successfulTransaction.gateway);

    // Find the actual payment intent / transaction ID to refund
    const transactionId =
      successfulTransaction.gatewayTransactionId || successfulTransaction.id;

    // For Stripe, we need the payment_intent, not the session ID
    // Try to get it from raw response if available
    let refundTransactionId = transactionId;
    if (
      successfulTransaction.gateway === (B2CPaymentGateway.STRIPE as B2CPaymentGateway) &&
      successfulTransaction.rawResponse
    ) {
      const rawResponse = successfulTransaction.rawResponse as Record<string, unknown>;
      if (rawResponse.payment_intent) {
        refundTransactionId = rawResponse.payment_intent as string;
      }
    }

    const refundResult = await gateway.refund(
      refundTransactionId,
      Number(successfulTransaction.amount),
    );

    if (refundResult.success) {
      // Update the transaction status
      await this.prisma.paymentTransaction.update({
        where: { id: successfulTransaction.id },
        data: {
          status: B2CPaymentStatus.REFUNDED as B2CPaymentStatus,
        },
      });

      // Update booking payment status
      await this.prisma.guestBooking.update({
        where: { bookingRef },
        data: {
          paymentStatus: B2CPaymentStatus.REFUNDED as B2CPaymentStatus,
        },
      });

      // Create a refund transaction record
      await this.prisma.paymentTransaction.create({
        data: {
          guestBookingId: booking.id,
          gateway: successfulTransaction.gateway,
          gatewayTransactionId: refundResult.refundId,
          amount: successfulTransaction.amount,
          currency: successfulTransaction.currency,
          status: B2CPaymentStatus.REFUNDED as B2CPaymentStatus,
          rawResponse: { refundId: refundResult.refundId },
        },
      });
    }

    return {
      success: refundResult.success,
      refundId: refundResult.refundId,
      bookingRef,
    };
  }
}
