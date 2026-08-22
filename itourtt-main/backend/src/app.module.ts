import { Module } from '@nestjs/common';
import { APP_INTERCEPTOR, APP_GUARD } from '@nestjs/core';
import { ConfigModule } from '@nestjs/config';
import { ScheduleModule } from '@nestjs/schedule';
import { AppController } from './app.controller.js';
import { AppService } from './app.service.js';
import { PrismaModule } from './prisma/prisma.module.js';
import { AuthModule } from './auth/auth.module.js';
import { SessionsModule } from './sessions/sessions.module.js';
import { UsersModule } from './users/users.module.js';
import { LocationsModule } from './locations/locations.module.js';
import { VehiclesModule } from './vehicles/vehicles.module.js';
import { DriversModule } from './drivers/drivers.module.js';
import { RepsModule } from './reps/reps.module.js';
import { AgentsModule } from './agents/agents.module.js';
import { CustomersModule } from './customers/customers.module.js';
import { SuppliersModule } from './suppliers/suppliers.module.js';
import { TrafficJobsModule } from './traffic-jobs/traffic-jobs.module.js';
import { DispatchModule } from './dispatch/dispatch.module.js';
import { FinanceModule } from './finance/finance.module.js';
import { ExportModule } from './export/export.module.js';
import { ReportsModule } from './reports/reports.module.js';
import { SettingsModule } from './settings/settings.module.js';
import { RepPortalModule } from './rep-portal/rep-portal.module.js';
import { DriverPortalModule } from './driver-portal/driver-portal.module.js';
import { WhatsappNotificationsModule } from './whatsapp-notifications/whatsapp-notifications.module.js';
import { PermissionsModule } from './permissions/permissions.module.js';
import { JobLocksModule } from './job-locks/job-locks.module.js';
import { SupplierPortalModule } from './supplier-portal/supplier-portal.module.js';
import { ActivityLogsModule } from './activity-logs/activity-logs.module.js';
import { PublicPricesModule } from './public-prices/public-prices.module.js';
import { ExtrasModule } from './extras/extras.module.js';
import { PaymentsModule } from './payments/payments.module.js';
import { GuestBookingsModule } from './guest-bookings/guest-bookings.module.js';
import { B2CModule } from './b2c/b2c.module.js';
import { EmailModule } from './email/email.module.js';
import { NotificationsModule } from './notifications/notifications.module.js';
import { ImportTemplatesModule } from './import-templates/import-templates.module.js';
import { AiParserModule } from './ai-parser/ai-parser.module.js';
import { PushNotificationsModule } from './push-notifications/push-notifications.module.js';
import { AuditInterceptor } from './common/interceptors/audit.interceptor.js';
import { JwtAuthGuard } from './common/guards/jwt-auth.guard.js';
import { DriverTariffsModule } from './driver-tariffs/driver-tariffs.module.js';
import { JobServiceTypesModule } from './job-service-types/job-service-types.module.js';
import { UserPreferencesModule } from './user-preferences/user-preferences.module.js';
import { ContactMessagesModule } from './contact-messages/contact-messages.module.js';
import { PartnerModule } from './partner/partner.module.js';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    ScheduleModule.forRoot(),
    PrismaModule,
    PermissionsModule,
    AuthModule,
    SessionsModule,
    UsersModule,
    LocationsModule,
    VehiclesModule,
    DriversModule,
    RepsModule,
    AgentsModule,
    CustomersModule,
    SuppliersModule,
    TrafficJobsModule,
    DispatchModule,
    FinanceModule,
    ExportModule,
    ReportsModule,
    SettingsModule,
    RepPortalModule,
    DriverPortalModule,
    WhatsappNotificationsModule,
    JobLocksModule,
    SupplierPortalModule,
    ActivityLogsModule,
    PublicPricesModule,
    ExtrasModule,
    DriverTariffsModule,
    JobServiceTypesModule,
    PaymentsModule,
    GuestBookingsModule,
    B2CModule,
    NotificationsModule,
    ImportTemplatesModule,
    AiParserModule,
    PushNotificationsModule,
    UserPreferencesModule,
    ContactMessagesModule,
    PartnerModule,
  ],
  controllers: [AppController],
  providers: [
    AppService,
    { provide: APP_INTERCEPTOR, useClass: AuditInterceptor },
    // Deny-by-default: every route requires a valid JWT unless marked @Public().
    { provide: APP_GUARD, useClass: JwtAuthGuard },
  ],
})
export class AppModule {}
