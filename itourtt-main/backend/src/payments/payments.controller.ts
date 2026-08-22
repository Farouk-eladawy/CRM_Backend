import {
  Controller,
  Post,
  Get,
  Param,
  Body,
  Query,
  Res,
  Headers,
  RawBody,
  UseGuards,
  HttpCode,
} from '@nestjs/common';
import type { Response } from 'express';
import { ConfigService } from '@nestjs/config';
import { PaymentsService } from './payments.service.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { Public } from '../common/decorators/public.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';
import type { GetPayInCallback } from './gateways/getpayin.gateway.js';
import { IsString, IsNotEmpty } from 'class-validator';

class CreatePaymentSessionDto {
  @IsString()
  @IsNotEmpty()
  bookingRef!: string;

  @IsString()
  @IsNotEmpty()
  gateway!: string;

  @IsString()
  @IsNotEmpty()
  returnUrl!: string;

  @IsString()
  @IsNotEmpty()
  cancelUrl!: string;
}

@Controller('payments')
export class PaymentsController {
  constructor(
    private readonly paymentsService: PaymentsService,
    private readonly configService: ConfigService,
  ) {}

  // ─── Create Payment Session (JWT Protected) ────────────
  @Post('create-session')
  @UseGuards(JwtAuthGuard)
  async createSession(@Body() dto: CreatePaymentSessionDto) {
    const result = await this.paymentsService.createPaymentSession(
      dto.bookingRef,
      dto.gateway,
      dto.returnUrl,
      dto.cancelUrl,
    );
    return new ApiResponse(result, 'Payment session created successfully');
  }

  // ─── Stripe Webhook (NO AUTH — verified by Stripe signature) ───
  @Public()
  @Post('webhook/stripe')
  @HttpCode(200)
  async stripeWebhook(
    @RawBody() rawBody: Buffer,
    @Headers('stripe-signature') signature: string,
  ) {
    const result = await this.paymentsService.handleStripeWebhook(
      rawBody,
      signature,
    );
    return result;
  }

  // ─── GetPayIn callbacks (NO AUTH — verified by HMAC signature) ───
  // GetPayIn sends two callbacks: a server-to-server webhook (POST, JSON body)
  // and a browser redirect (GET, query string). To be resilient to how the
  // Webhook URL / Redirect URL are mapped in the dashboard, BOTH paths
  // (/webhook/getpayin and /return/getpayin) accept BOTH methods:
  //   • POST → record the result, reply 200 JSON (what the webhook expects)
  //   • GET  → record the result, then 302-redirect the guest to the B2C site
  // Recommended dashboard config:
  //   Webhook URL  = https://<backend-host>/api/payments/webhook/getpayin
  //   Redirect URL = https://<backend-host>/api/payments/return/getpayin

  @Public()
  @Post('webhook/getpayin')
  @HttpCode(200)
  async getPayInWebhook(@Body() body: GetPayInCallback) {
    return this.recordGetPayInCallback(body);
  }

  @Public()
  @Post('return/getpayin')
  @HttpCode(200)
  async getPayInReturnPost(@Body() body: GetPayInCallback) {
    return this.recordGetPayInCallback(body);
  }

  @Public()
  @Get('return/getpayin')
  async getPayInReturn(@Query() query: GetPayInCallback, @Res() res: Response) {
    return this.redirectGetPayInCallback(query, res);
  }

  @Public()
  @Get('webhook/getpayin')
  async getPayInWebhookGet(@Query() query: GetPayInCallback, @Res() res: Response) {
    return this.redirectGetPayInCallback(query, res);
  }

  /** Server-to-server callback handler → JSON 200 (webhook semantics). */
  private async recordGetPayInCallback(payload: GetPayInCallback) {
    const result = await this.paymentsService.processGetPayInCallback(payload);
    return { success: true, message: 'Callback processed', paid: result.paid };
  }

  /** Browser callback handler → settle, then 302 to the B2C success/cancel page. */
  private async redirectGetPayInCallback(
    payload: GetPayInCallback,
    res: Response,
  ) {
    const siteUrl = (
      this.configService.get<string>('B2C_SITE_URL') || 'https://transfera.ae'
    ).replace(/\/+$/, '');

    let paid = false;
    let bookingRef: string | null = null;
    try {
      const result = await this.paymentsService.processGetPayInCallback(payload);
      paid = result.paid;
      bookingRef = result.bookingRef;
    } catch {
      // Signature/processing failure → treat as a failed payment for the guest.
      paid = false;
    }

    const refParam = bookingRef ? `?ref=${encodeURIComponent(bookingRef)}` : '';
    const target = paid
      ? `${siteUrl}/payment/success${refParam}`
      : `${siteUrl}/payment/cancel${refParam}`;
    return res.redirect(302, target);
  }

  // ─── Verify Payment Status (Public) ────────────────────
  @Public()
  @Post('verify/:bookingRef')
  @HttpCode(200)
  async verifyPayment(@Param('bookingRef') bookingRef: string) {
    const result =
      await this.paymentsService.verifyPaymentStatus(bookingRef);
    return new ApiResponse(result);
  }
}
