import {
  Controller,
  Get,
  Post,
  Patch,
  Param,
  Query,
  UseGuards,
  ParseUUIDPipe,
} from '@nestjs/common';
import { GuestBookingsService } from './guest-bookings.service.js';
import { GuestBookingQueryDto } from './dto/guest-booking-query.dto.js';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { RolesGuard } from '../common/guards/roles.guard.js';
import { PermissionsGuard } from '../common/guards/permissions.guard.js';
import { Roles } from '../common/decorators/roles.decorator.js';
import { Permissions } from '../common/decorators/permissions.decorator.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { ApiResponse } from '../common/dto/api-response.dto.js';

@Controller('guest-bookings')
@UseGuards(JwtAuthGuard, RolesGuard, PermissionsGuard)
export class GuestBookingsController {
  constructor(private readonly guestBookingsService: GuestBookingsService) {}

  @Get()
  @Permissions('guest-bookings')
  async findAll(@Query() query: GuestBookingQueryDto) {
    return this.guestBookingsService.findAll(query);
  }

  @Get(':id')
  @Permissions('guest-bookings')
  async findOne(@Param('id') id: string) {
    const booking = await this.guestBookingsService.findOne(id);
    return new ApiResponse(booking);
  }

  @Post(':id/convert')
  @Permissions('guest-bookings.convert')
  @Roles('ADMIN', 'DISPATCHER')
  async convertToJob(
    @Param('id') id: string,
    @CurrentUser('id') userId: string,
  ) {
    const job = await this.guestBookingsService.convertToJob(id, userId);
    return new ApiResponse(job, 'Guest booking converted to traffic job successfully');
  }

  @Patch(':id/cancel')
  @Permissions('guest-bookings.cancel')
  @Roles('ADMIN')
  async cancelBooking(@Param('id') id: string) {
    const result = await this.guestBookingsService.cancelBooking(id);
    return new ApiResponse(result);
  }
}
