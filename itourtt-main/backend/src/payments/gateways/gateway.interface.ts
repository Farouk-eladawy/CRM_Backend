export interface PaymentSessionResult {
  sessionId: string;
  checkoutUrl: string;
  gateway: string;
}

/**
 * Optional customer/order context some gateways require to build a hosted
 * checkout (e.g. GetPayIn needs the payer's name + email). Gateways that don't
 * need it simply ignore the argument.
 */
export interface PaymentCustomer {
  firstName: string;
  lastName: string;
  email: string;
  orderTitle: string;
  address?: string;
  city?: string;
  country?: string;
  /**
   * Optional line items shown on the hosted checkout page (e.g. Guest, Route,
   * Pickup). Gateways that support it render one row per entry; others ignore
   * it. Not part of any signature.
   */
  orderDetails?: Array<{ label: string; value: string }>;
}

export interface PaymentVerificationResult {
  success: boolean;
  transactionId: string;
  amount: number;
  currency: string;
}

export interface PaymentGateway {
  createSession(
    bookingRef: string,
    amount: number,
    currency: string,
    returnUrl: string,
    cancelUrl: string,
    customer?: PaymentCustomer,
  ): Promise<PaymentSessionResult>;

  verifyPayment(sessionId: string): Promise<PaymentVerificationResult>;

  refund(
    transactionId: string,
    amount: number,
  ): Promise<{ success: boolean; refundId: string }>;
}
