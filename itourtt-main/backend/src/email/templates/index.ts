import type { BookingEmailData, PaymentReceiptData, PaymentFailedData, StaffAssignmentData, JobUpdateEmailData } from '../email.service.js';
import { serviceTypeLabel } from '../../common/utils/service-type.util.js';

/** Branding injected into the email header/footer. Guest-facing emails pass
 *  B2C (Transfera) branding; internal emails fall back to DEFAULT_BRANDING. */
export interface EmailBranding {
  siteName: string;
  contactEmail: string;
  headerBg: string;
  /** Absolute URL to a raster (PNG/JPG) logo. If null, the site name is shown as text. */
  logoUrl?: string | null;
  /** Sub-line shown under the site name when no logo is used. */
  tagline?: string | null;
  /** Absolute URL to the Terms & Conditions page. When set, a footer link is added. */
  termsUrl?: string | null;
  /** Absolute URL to the account login page. When set, a footer link is added. */
  loginUrl?: string | null;
}

const DEFAULT_BRANDING: EmailBranding = {
  siteName: 'iTour Transport & Traffic',
  contactEmail: 'support@itour.local',
  headerBg: '#1a1a2e',
  logoUrl: null,
  tagline: 'Your trusted transfer partner',
  termsUrl: null,
  loginUrl: null,
};

/** Human-readable service type for guests (the DB stores short codes). */
const serviceLabel = (serviceType: string): string => serviceTypeLabel(serviceType);

const baseStyle = `
  body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background: #f4f4f7; }
  .container { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; }
  .header { background: #1a1a2e; color: #ffffff; padding: 24px 32px; text-align: center; }
  .header h1 { margin: 0; font-size: 20px; font-weight: 600; }
  .header p { margin: 4px 0 0; font-size: 13px; color: #a0a0b8; }
  .body { padding: 32px; }
  .body h2 { color: #1a1a2e; font-size: 18px; margin: 0 0 16px; }
  .body p { color: #4a4a68; font-size: 14px; line-height: 1.6; margin: 0 0 12px; }
  .details { background: #f8f8fc; border-radius: 6px; padding: 16px 20px; margin: 16px 0; }
  .details table { width: 100%; border-collapse: collapse; }
  .details td { padding: 6px 0; font-size: 14px; color: #4a4a68; }
  .details td:first-child { font-weight: 600; color: #1a1a2e; width: 40%; }
  .total { background: #1a1a2e; color: #ffffff; border-radius: 6px; padding: 12px 20px; margin: 16px 0; text-align: center; font-size: 18px; font-weight: 600; }
  .footer { padding: 20px 32px; text-align: center; font-size: 12px; color: #a0a0b8; border-top: 1px solid #eee; }
`;

function wrap(content: string, branding: EmailBranding = DEFAULT_BRANDING): string {
  const headerInner = branding.logoUrl
    ? `<img src="${branding.logoUrl}" alt="${branding.siteName}" style="max-height:44px;max-width:220px;height:auto;display:inline-block;" />`
    : `<h1>${branding.siteName}</h1>${branding.tagline ? `<p>${branding.tagline}</p>` : ''}`;

  const linkStyle = 'color:#a0a0b8;text-decoration:underline;';
  const footerLinks = [
    branding.termsUrl ? `<a href="${branding.termsUrl}" style="${linkStyle}">Terms &amp; Conditions</a>` : '',
    branding.loginUrl ? `<a href="${branding.loginUrl}" style="${linkStyle}">Log in to my account</a>` : '',
  ].filter(Boolean).join(' &nbsp;&middot;&nbsp; ');

  return `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>${baseStyle}</style></head>
<body>
<div class="container">
  <div class="header" style="background:${branding.headerBg};">
    ${headerInner}
  </div>
  ${content}
  <div class="footer">
    <p>${branding.siteName} &copy; ${new Date().getFullYear()}</p>
    <p>If you have questions, contact us at <a href="mailto:${branding.contactEmail}" style="color:#a0a0b8;">${branding.contactEmail}</a></p>
    ${footerLinks ? `<p>${footerLinks}</p>` : ''}
  </div>
</div>
</body>
</html>`;
}

export function bookingConfirmationTemplate(data: BookingEmailData, branding?: EmailBranding): string {
  return wrap(`
  <div class="body">
    <h2>Booking Confirmed!</h2>
    <p>Dear ${data.guestName},</p>
    <p>Your transfer booking has been confirmed. Here are the details:</p>
    <div class="details">
      <table>
        <tr><td>Booking Ref</td><td>${data.bookingRef}</td></tr>
        <tr><td>Service</td><td>${serviceLabel(data.serviceType)}</td></tr>
        <tr><td>Date</td><td>${data.jobDate}</td></tr>
        ${data.pickupTime ? `<tr><td>Pickup Time</td><td>${data.pickupTime}</td></tr>` : ''}
        <tr><td>From</td><td>${data.fromZone}</td></tr>
        <tr><td>To</td><td>${data.toZone}</td></tr>
        ${data.hotel ? `<tr><td>Hotel</td><td>${data.hotel}</td></tr>` : ''}
        ${data.flightNo ? `<tr><td>Flight</td><td>${data.flightNo}</td></tr>` : ''}
        <tr><td>Passengers</td><td>${data.paxCount}</td></tr>
        <tr><td>Vehicle</td><td>${data.vehicleType}</td></tr>
        <tr><td>Payment</td><td>${data.paymentMethod === 'PAY_ON_ARRIVAL' ? 'Pay on Arrival' : 'Online Payment'}</td></tr>
      </table>
    </div>
    <div class="total">${data.currency} ${data.total.toFixed(2)}</div>
    <p>We look forward to serving you!</p>
  </div>`, branding);
}

export function paymentReceiptTemplate(data: PaymentReceiptData, branding?: EmailBranding): string {
  return wrap(`
  <div class="body">
    <h2>Payment Received</h2>
    <p>Dear ${data.guestName},</p>
    <p>We have received your payment. Here is your receipt:</p>
    <div class="details">
      <table>
        <tr><td>Booking Ref</td><td>${data.bookingRef}</td></tr>
        <tr><td>Amount</td><td>${data.currency} ${data.amount.toFixed(2)}</td></tr>
        <tr><td>Gateway</td><td>${data.gateway}</td></tr>
        <tr><td>Transaction ID</td><td>${data.transactionId}</td></tr>
        <tr><td>Date</td><td>${data.paidAt}</td></tr>
      </table>
    </div>
    <p>Thank you for your payment!</p>
  </div>`, branding);
}

export function onlinePaymentFailedTemplate(data: PaymentFailedData, branding?: EmailBranding): string {
  return wrap(`
  <div class="body">
    <h2>Payment Not Completed</h2>
    <p>Dear ${data.guestName},</p>
    <p>We were unable to confirm your online payment for booking
       <strong>${data.bookingRef}</strong>, so no charge was taken.</p>
    <p><strong>Your booking is still confirmed.</strong> We've switched it to
       <strong>Pay on Arrival</strong> &mdash; please pay your driver in cash when you arrive.</p>
    <div class="total">${data.currency} ${data.amount.toFixed(2)} &middot; Pay on Arrival</div>
    <p>If you'd prefer to pay online instead, just contact us and we'll send you a new payment link.</p>
  </div>`, branding);
}

export function bookingCancellationTemplate(data: BookingEmailData, branding?: EmailBranding): string {
  return wrap(`
  <div class="body">
    <h2>Booking Cancelled</h2>
    <p>Dear ${data.guestName},</p>
    <p>Your booking <strong>${data.bookingRef}</strong> has been cancelled.</p>
    <div class="details">
      <table>
        <tr><td>Booking Ref</td><td>${data.bookingRef}</td></tr>
        <tr><td>Service</td><td>${serviceLabel(data.serviceType)}</td></tr>
        <tr><td>Date</td><td>${data.jobDate}</td></tr>
        <tr><td>From</td><td>${data.fromZone}</td></tr>
        <tr><td>To</td><td>${data.toZone}</td></tr>
      </table>
    </div>
    <p>If this was a mistake or you need assistance, please contact our support team.</p>
    <div style="background:#fff8e1;border-left:4px solid #f0c000;border-radius:6px;padding:14px 18px;margin:16px 0;">
      <p style="margin:0;color:#4a4a68;font-size:14px;line-height:1.6;">
        <strong style="color:#1a1a2e;">Refund Policy:</strong> The amount will be refunded to the same card you used in the payment process within 28 working days, excluding weekends and national holidays.
      </p>
    </div>
  </div>`, branding);
}

export function staffAssignmentTemplate(data: StaffAssignmentData, branding?: EmailBranding): string {
  const sectionTitle = 'font-weight:600;color:#1a1a2e;margin:18px 0 6px;';
  // Arrival: guest is met at the airport. Departure: guest is picked up at the start point.
  const meetingLabel = data.serviceType === 'DEP' ? 'Pickup Point' : 'Meeting Point';

  const tripRows = `
        ${data.meetingPoint ? `<tr><td>${meetingLabel}</td><td>${data.meetingPoint}</td></tr>` : ''}
        ${data.pickupTime ? `<tr><td>Pickup Time</td><td>${data.pickupTime}</td></tr>` : ''}`;

  return wrap(`
  <div class="body">
    <h2>Your Transfer Team is Ready</h2>
    <p>Dear ${data.guestName},</p>
    <p>Your representative and driver have been assigned to your booking <strong>${data.bookingRef}</strong>.</p>

    ${tripRows.trim() ? `<div class="details"><table>${tripRows}</table></div>` : ''}

    <p style="${sectionTitle}">Representative</p>
    <div class="details">
      <table>
        <tr><td>Name</td><td>${data.repName}</td></tr>
        ${data.repPhone ? `<tr><td>Phone</td><td>${data.repPhone}</td></tr>` : ''}
      </table>
    </div>

    <p style="${sectionTitle}">Driver</p>
    <div class="details">
      <table>
        <tr><td>Name</td><td>${data.driverName}</td></tr>
        ${data.driverPhone ? `<tr><td>Phone</td><td>${data.driverPhone}</td></tr>` : ''}
      </table>
    </div>

    ${data.vehicleType || data.vehiclePlate ? `
    <p style="${sectionTitle}">Vehicle</p>
    <div class="details">
      <table>
        ${data.vehicleType ? `<tr><td>Type</td><td>${data.vehicleType}${data.vehicleColor ? ` (${data.vehicleColor})` : ''}</td></tr>` : ''}
        ${data.vehiclePlate ? `<tr><td>Plate Number</td><td>${data.vehiclePlate}</td></tr>` : ''}
      </table>
    </div>` : ''}

    <p>Your representative and driver will be ready to assist you. Have a great trip!</p>
  </div>`, branding);
}

export function jobUpdateNotificationTemplate(data: JobUpdateEmailData): string {
  const hl = (field: string) => data.changedFields.includes(field) ? 'background:#FFFF00;' : '';
  return wrap(`
  <div class="body">
    <h2>Traffic Job Updated</h2>
    <p>Job <strong>${data.internalRef}</strong> has been updated by <strong>${data.updatedBy}</strong>.</p>
    <div class="details">
      <table>
        <tr style="${hl('bookingStatus')}"><td>Booking Status</td><td>${data.bookingStatus}</td></tr>
        <tr style="${hl('status')}"><td>Job Status</td><td>${data.jobStatus}</td></tr>
        <tr><td>Internal Ref</td><td>${data.internalRef}</td></tr>
        <tr><td>Channel</td><td>${data.bookingChannel}</td></tr>
        ${data.agentName ? `<tr style="${hl('agentId')}"><td>Agent</td><td>${data.agentName}</td></tr>` : ''}
        ${data.agentRef ? `<tr style="${hl('agentRef')}"><td>Agent Ref</td><td>${data.agentRef}</td></tr>` : ''}
        ${data.customerName ? `<tr style="${hl('customerId')}"><td>Customer</td><td>${data.customerName}</td></tr>` : ''}
        <tr style="${hl('serviceType')}"><td>Service Type</td><td>${serviceLabel(data.serviceType)}</td></tr>
        <tr style="${hl('jobDate')}"><td>Service Date</td><td>${data.jobDate}</td></tr>
        ${data.pickUpTime ? `<tr style="${hl('pickUpTime')}"><td>Pick-up Time</td><td>${data.pickUpTime}</td></tr>` : ''}
        <tr style="${hl('adultCount')}${hl('childCount')}"><td>Passengers</td><td>${data.paxCount} (${data.adultCount}A${data.childCount > 0 ? `+${data.childCount}C` : ''})</td></tr>
        ${data.clientName ? `<tr style="${hl('clientName')}"><td>Client Name</td><td>${data.clientName}</td></tr>` : ''}
        ${data.clientMobile ? `<tr style="${hl('clientMobile')}"><td>Client Mobile</td><td>${data.clientMobile}</td></tr>` : ''}
        ${data.originLocation ? `<tr style="${hl('originAirportId')}${hl('originZoneId')}${hl('originHotelId')}"><td>Origin</td><td>${data.originLocation}</td></tr>` : ''}
        ${data.destinationLocation ? `<tr style="${hl('destinationAirportId')}${hl('destinationZoneId')}${hl('destinationHotelId')}"><td>Destination</td><td>${data.destinationLocation}</td></tr>` : ''}
        ${data.flightNo ? `<tr style="${hl('flight')}"><td>Flight</td><td>${data.flightNo}</td></tr>` : ''}
        ${data.notes ? `<tr style="${hl('notes')}"><td>Notes</td><td>${data.notes}</td></tr>` : ''}
        <tr><td>Updated At</td><td>${data.updatedAt}</td></tr>
      </table>
    </div>
    ${data.changedFields.length > 0 ? '<p style="font-size:12px;color:#888;">Fields highlighted in <span style="background:#FFFF00;padding:2px 6px;">yellow</span> were changed in this update.</p>' : ''}
  </div>`);
}
