import {
  Controller,
  Get,
  Post,
  Delete,
  Body,
  Ip,
  Headers,
  Res,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import type { Response } from 'express';
import type { SessionContext } from '../sessions/sessions.service.js';

const UPLOADS_COOKIE = 'uploads_token';
import { AuthService } from './auth.service.js';
import { LoginDto } from './dto/login.dto.js';
import { RefreshDto } from './dto/refresh.dto.js';
import {
  RegisterDeviceTokenDto,
  RemoveDeviceTokenDto,
} from './dto/device-token.dto.js';
import type { AuthResponseDto } from './dto/auth-response.dto.js';
import { Throttle } from '@nestjs/throttler';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard.js';
import { CurrentUser } from '../common/decorators/current-user.decorator.js';
import { Public } from '../common/decorators/public.decorator.js';
import { PrismaService } from '../prisma/prisma.service.js';

@Controller('auth')
export class AuthController {
  constructor(
    private readonly authService: AuthService,
    private readonly prisma: PrismaService,
  ) {}

  @Public()
  @Get('login-config')
  async getLoginConfig() {
    const settings = await this.prisma.systemSettings.findFirst();
    return {
      loginBgImageUrl: settings?.loginBgImageUrl ?? null,
      loginLogoUrl: settings?.loginLogoUrl ?? null,
    };
  }

  // Brute-force protection: cap login attempts to 10/min per IP (tighter than
  // the global default) so credential-stuffing is impractical.
  @Public()
  @Throttle({ default: { limit: 10, ttl: 60000 } })
  @Post('login')
  @HttpCode(HttpStatus.OK)
  async login(
    @Body() loginDto: LoginDto,
    @Ip() ip: string,
    @Res({ passthrough: true }) res: Response,
    @Headers('user-agent') userAgent?: string,
    @Headers('x-forwarded-for') forwardedFor?: string,
  ): Promise<AuthResponseDto | { twoFactorRequired: true; challengeToken: string }> {
    const result = await this.authService.login(
      loginDto.identifier,
      loginDto.password,
      this.sessionCtx(ip, userAgent, forwardedFor),
    );
    if ('accessToken' in result) await this.setUploadsCookie(res, result.user.id);
    return result;
  }

  // Real client IP behind Traefik/nginx is the first X-Forwarded-For hop.
  private sessionCtx(ip: string, userAgent?: string, forwardedFor?: string): SessionContext {
    const realIp = forwardedFor?.split(',')[0]?.trim() || ip || null;
    return { ip: realIp, userAgent: userAgent ?? null };
  }

  // httpOnly cookie so <img src="/uploads/…"> requests carry auth (a Bearer
  // token can't ride on an image request). Scoped to the /uploads path.
  private async setUploadsCookie(res: Response, userId: string) {
    res.cookie(UPLOADS_COOKIE, await this.authService.signUploadsToken(userId), {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/uploads',
      maxAge: 7 * 24 * 60 * 60 * 1000,
    });
  }

  // Login step 2: exchange the challenge + a TOTP/recovery code for a session.
  @Public()
  @Throttle({ default: { limit: 10, ttl: 60000 } })
  @Post('2fa/verify')
  @HttpCode(HttpStatus.OK)
  async verifyTwoFactor(
    @Body() body: { challengeToken: string; code: string },
    @Ip() ip: string,
    @Res({ passthrough: true }) res: Response,
    @Headers('user-agent') userAgent?: string,
    @Headers('x-forwarded-for') forwardedFor?: string,
  ) {
    const result = await this.authService.verifyTwoFactor(
      body.challengeToken,
      body.code,
      this.sessionCtx(ip, userAgent, forwardedFor),
    );
    await this.setUploadsCookie(res, result.user.id);
    return result;
  }

  @Post('2fa/setup')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async setupTwoFactor(@CurrentUser('sub') userId: string) {
    return this.authService.setupTwoFactor(userId);
  }

  @Post('2fa/enable')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async enableTwoFactor(
    @CurrentUser('sub') userId: string,
    @Body() body: { code: string },
  ) {
    return this.authService.enableTwoFactor(userId, body.code);
  }

  @Post('2fa/disable')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async disableTwoFactor(
    @CurrentUser('sub') userId: string,
    @Body() body: { code: string },
  ) {
    await this.authService.disableTwoFactor(userId, body.code);
    return { message: 'Two-factor authentication disabled' };
  }

  @Public()
  @Post('refresh')
  @HttpCode(HttpStatus.OK)
  async refresh(
    @Body() refreshDto: RefreshDto,
    @Res({ passthrough: true }) res: Response,
  ): Promise<AuthResponseDto> {
    const result = await this.authService.refresh(refreshDto.refreshToken);
    await this.setUploadsCookie(res, result.user.id);
    return result;
  }

  @Public()
  @Throttle({ default: { limit: 5, ttl: 60000 } })
  @Post('forgot-password')
  @HttpCode(HttpStatus.OK)
  async forgotPassword(@Body() body: { email: string }) {
    await this.authService.forgotPassword(body.email ?? '');
    return { message: 'If this email is registered, a reset link has been sent.' };
  }

  @Public()
  @Throttle({ default: { limit: 5, ttl: 60000 } })
  @Post('reset-password')
  @HttpCode(HttpStatus.OK)
  async resetPassword(@Body() body: { email: string; token: string; newPassword: string }) {
    await this.authService.resetPassword(body.email, body.token, body.newPassword);
    return { message: 'Password has been reset successfully. Please log in.' };
  }

  @Post('logout')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async logout(
    @CurrentUser('sub') userId: string,
    @Res({ passthrough: true }) res: Response,
    @CurrentUser('sid') sessionId?: string,
  ) {
    await this.authService.logout(userId, sessionId);
    res.clearCookie(UPLOADS_COOKIE, { path: '/uploads' });
    return { message: 'Logged out successfully' };
  }

  @Post('device-token')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async registerDeviceToken(
    @CurrentUser('sub') userId: string,
    @Body() dto: RegisterDeviceTokenDto,
  ) {
    await this.prisma.deviceToken.upsert({
      where: {
        userId_token: { userId, token: dto.token },
      },
      create: {
        userId,
        token: dto.token,
        platform: dto.platform,
      },
      update: {
        platform: dto.platform,
      },
    });
    return { message: 'Device token registered' };
  }

  @Delete('device-token')
  @UseGuards(JwtAuthGuard)
  @HttpCode(HttpStatus.OK)
  async removeDeviceToken(
    @CurrentUser('sub') userId: string,
    @Body() dto: RemoveDeviceTokenDto,
  ) {
    await this.prisma.deviceToken.deleteMany({
      where: { userId, token: dto.token },
    });
    return { message: 'Device token removed' };
  }
}
