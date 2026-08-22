import { BadRequestException } from '@nestjs/common';

/**
 * NO SHOW can only be reported 80 minutes after the job time, for both
 * arrivals and departures. The delay exists so drivers/reps cannot tap the
 * button by mistake right after the job appears.
 */
export const NO_SHOW_DELAY_MS = 80 * 60 * 1000;

interface NoShowJob {
  serviceType: string;
  pickUpTime?: Date | null;
  flight?: { arrivalTime?: Date | null } | null;
}

/** Job time used for the guard: flight arrival for ARR, pick-up time otherwise. */
export function getNoShowJobTime(job: NoShowJob): Date | null {
  const raw =
    job.serviceType === 'ARR'
      ? (job.flight?.arrivalTime ?? null)
      : (job.pickUpTime ?? null);
  return raw ? new Date(raw) : null;
}

/** Throws unless we are at least NO_SHOW_DELAY_MS past the job time. */
export function checkNoShowWindow(job: NoShowJob): void {
  const jobTime = getNoShowJobTime(job);
  if (!jobTime) return;

  const availableFrom = new Date(jobTime.getTime() + NO_SHOW_DELAY_MS);
  if (new Date() < availableFrom) {
    const timeStr = availableFrom.toLocaleTimeString('en-GB', {
      timeZone: 'Africa/Cairo',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    throw new BadRequestException(
      `NO SHOW can only be reported 80 minutes after the job time (from ${timeStr})`,
    );
  }
}
