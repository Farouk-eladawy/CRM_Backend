import type { PortalJob } from '../types';

/** Get human-readable origin label from a job */
export function getOriginLabel(job: PortalJob): string {
  if (job.originAirport) return `${job.originAirport.name} (${job.originAirport.code})`;
  if (job.originHotel) return job.originHotel.name;
  if (job.originZone) return job.originZone.name;
  return '\u2014';
}

/** Get human-readable destination label from a job */
export function getDestinationLabel(job: PortalJob): string {
  if (job.destinationAirport) return `${job.destinationAirport.name} (${job.destinationAirport.code})`;
  if (job.destinationHotel) return job.destinationHotel.name;
  if (job.destinationZone) return job.destinationZone.name;
  return '\u2014';
}

/** Get short route string: "Origin → Destination" */
export function getRouteLabel(job: PortalJob): string {
  return `${getOriginLabel(job)} \u2192 ${getDestinationLabel(job)}`;
}
