import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { B2CController } from './b2c.controller.js';
import { B2CService } from './b2c.service.js';
import { B2CInvoiceService } from './b2c-invoice.service.js';
import { PrismaModule } from '../prisma/prisma.module.js';
import { EmailModule } from '../email/email.module.js';
import { GoogleDriveModule } from '../google-drive/google-drive.module.js';

@Module({
  imports: [
    PrismaModule,
    EmailModule,
    GoogleDriveModule,
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        secret: configService.get<string>('JWT_SECRET'),
        signOptions: { expiresIn: '30d' },
      }),
      inject: [ConfigService],
    }),
  ],
  controllers: [B2CController],
  providers: [B2CService, B2CInvoiceService],
  exports: [B2CService, B2CInvoiceService],
})
export class B2CModule {}
