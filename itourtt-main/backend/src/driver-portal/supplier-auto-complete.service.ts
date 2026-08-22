import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { PrismaService } from '../prisma/prisma.service.js';

const TERMINAL_STATUSES = ['COMPLETED', 'CANCELLED', 'NO_SHOW'];
// Jobs in these overall states are never touched (a cancelled / no-show job's
// driver did not drive, so its driver leg must not be auto-completed). A job
// that is already COMPLETED (e.g. closed by the rep) IS still processed so the
// supplier driver leg gets completed.
const JOB_SKIP_STATUSES = ['CANCELLED', 'NO_SHOW'];
const CAIRO_TZ = 'Africa/Cairo';

@Injectable()
export class SupplierAutoCompleteService {
  private readonly logger = new Logger(SupplierAutoCompleteService.name);

  constructor(private readonly prisma: PrismaService) {}

  // Midnight Cairo: the ONLY automatic action is to set the DRIVER status to
  // COMPLETED for supplier-sourced cars. It never touches rep status, supplier
  // status, or the overall job status. Job completion is rep-driven (handled by
  // the rep portal), not by this cron.
  //
  // "Supplier-sourced" = an external supplier car: supplierId set AND no own
  // vehicle AND no own driver assigned. Own vehicles / own drivers must complete
  // their jobs via the driver portal (with GPS evidence) and are never touched.
  @Cron('0 0 * * *', { timeZone: CAIRO_TZ })
  async autoCompleteJobs() {
    // Get Cairo "today" as a UTC-midnight Date so it matches @db.Date stored values
    const nowUtc = new Date();
    const cairoDateStr = nowUtc.toLocaleDateString('en-CA', { timeZone: CAIRO_TZ });
    const [y, m, d] = cairoDateStr.split('-').map(Number);
    const todayCairo = new Date(Date.UTC(y, m - 1, d));

    // Single-replica guard: claim tonight's run. With multiple backend pods,
    // @nestjs/schedule fires the cron on every replica; the unique
    // (job_name, run_date) row ensures only the first pod actually runs.
    try {
      await this.prisma.cronRunLock.create({
        data: { jobName: 'supplier-auto-complete', runDate: todayCairo },
      });
    } catch {
      this.logger.log(
        'Midnight driver auto-complete already claimed by another replica for today — skipping.',
      );
      return;
    }

    this.logger.log(
      `Midnight driver auto-complete: processing supplier-sourced past jobs before ${todayCairo.toISOString()}`,
    );

    await this.autoCompleteSupplierDrivers(todayCairo);
  }

  // Set driverStatus = COMPLETED for supplier-sourced cars only.
  private async autoCompleteSupplierDrivers(before: Date) {
    const assignments = await this.prisma.trafficAssignment.findMany({
      where: {
        // Car Source = Supplier: a supplier is set and neither an own vehicle
        // nor an own driver is assigned.
        supplierId: { not: null },
        vehicleId: null,
        driverId: null,
        driverStatus: { notIn: TERMINAL_STATUSES as any },
        trafficJob: {
          deletedAt: null,
          status: { notIn: JOB_SKIP_STATUSES as any },
          jobDate: { lt: before },
        },
      },
      include: { trafficJob: true },
    });

    for (const assignment of assignments) {
      const job = assignment.trafficJob;
      this.logger.log(
        `Auto-completing supplier driver for job ${job.internalRef} (was: ${assignment.driverStatus})`,
      );
      try {
        await this.prisma.$transaction(async (tx) => {
          await tx.trafficAssignment.update({
            where: { id: assignment.id },
            data: { driverStatus: 'COMPLETED' as any },
          });

          await tx.statusChangeLog.create({
            data: {
              assignmentId: assignment.id,
              changedBy: 'SYSTEM',
              changedById: assignment.id,
              previousStatus: assignment.driverStatus as any,
              newStatus: 'COMPLETED' as any,
              gpsLatitude: 0,
              gpsLongitude: 0,
              gpsMapLink: 'Auto-completed by system (midnight)',
            },
          });
        });
      } catch (err) {
        this.logger.error(
          `Failed supplier driver auto-complete for job ${job.internalRef}: ${err}`,
        );
      }
    }
  }
}
