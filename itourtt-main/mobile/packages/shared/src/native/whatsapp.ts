import { Linking, Alert } from 'react-native';

/**
 * Open WhatsApp chat with the given phone number.
 * Phone number should include country code (e.g. +201234567890).
 * Optionally pre-fills a message.
 */
export async function openWhatsApp(phoneNumber: string, message?: string) {
  const cleaned = phoneNumber.replace(/[^\d]/g, '');
  const encoded = message ? encodeURIComponent(message) : '';
  const url = `whatsapp://send?phone=${cleaned}${encoded ? `&text=${encoded}` : ''}`;

  const supported = await Linking.canOpenURL(url);
  if (supported) {
    await Linking.openURL(url);
  } else {
    // Fallback to web WhatsApp
    const webUrl = `https://wa.me/${cleaned}${encoded ? `?text=${encoded}` : ''}`;
    Linking.openURL(webUrl).catch(() => {
      Alert.alert('Error', 'WhatsApp is not installed on this device');
    });
  }
}

/**
 * Send a WhatsApp message about a job to a phone number.
 * Pre-fills message with job reference and details.
 */
export function sendJobWhatsApp(
  phoneNumber: string,
  jobRef: string,
  details?: { route?: string; date?: string; time?: string },
) {
  let message = `iTour Job: ${jobRef}`;
  if (details?.route) message += `\nRoute: ${details.route}`;
  if (details?.date) message += `\nDate: ${details.date}`;
  if (details?.time) message += `\nTime: ${details.time}`;

  openWhatsApp(phoneNumber, message);
}
