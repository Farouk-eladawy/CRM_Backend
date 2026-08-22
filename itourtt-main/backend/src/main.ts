import { NestFactory } from '@nestjs/core';
import { ValidationPipe, Logger } from '@nestjs/common';
import * as express from 'express';
import * as path from 'path';
import * as dns from 'dns';
import compression from 'compression';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app.module.js';
import { PrismaService } from './prisma/prisma.service.js';
import { AllExceptionsFilter } from './common/filters/http-exception.filter.js';

// Force IPv4 for all outbound connections — the pod has no IPv6 route
// and smtp.office365.com (and other hosts) may resolve to IPv6 first.
dns.setDefaultResultOrder('ipv4first');

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    rawBody: true,
  });
  const logger = new Logger('Bootstrap');

  // Compress all responses (gzip) — reduces payload 70-90% for large JSON
  app.use(compression());

  // Serve /uploads with auth. Rep/driver/supplier legal docs, job attachments
  // and stamps are private — gate them behind an httpOnly `uploads_token`
  // cookie (so <img> requests carry auth) OR a Bearer token. Login-branding
  // assets stay public so the pre-auth login screen can load them.
  const jwtService = app.get(JwtService, { strict: false });
  const prisma = app.get(PrismaService);
  const jwtSecret = app.get(ConfigService).get<string>('JWT_SECRET');
  const uploadsDir = path.join(process.cwd(), 'uploads');

  // Public branding paths (login logo/bg, company logo/favicon), cached 60s.
  let publicUploads = new Set<string>();
  let publicFetchedAt = 0;
  const refreshPublicUploads = async () => {
    if (Date.now() - publicFetchedAt < 60_000) return;
    publicFetchedAt = Date.now();
    try {
      const s = await prisma.systemSettings.findFirst({
        select: {
          loginLogoUrl: true,
          loginBgImageUrl: true,
          innerBgImageUrl: true,
        },
      });
      const set = new Set<string>();
      for (const u of [s?.loginLogoUrl, s?.loginBgImageUrl, s?.innerBgImageUrl]) {
        if (u && u.startsWith('/uploads/')) set.add(u.slice('/uploads'.length));
      }
      publicUploads = set;
    } catch {
      /* keep last known set */
    }
  };

  const readCookie = (header: string | undefined, name: string): string | null => {
    if (!header) return null;
    for (const part of header.split(';')) {
      const eq = part.indexOf('=');
      if (eq === -1) continue;
      if (part.slice(0, eq).trim() === name) {
        return decodeURIComponent(part.slice(eq + 1).trim());
      }
    }
    return null;
  };

  app.use(
    '/uploads',
    async (
      req: express.Request,
      res: express.Response,
      next: express.NextFunction,
    ) => {
      await refreshPublicUploads();
      // req.path may be URL-encoded (e.g. %20 for spaces in a filename), while the
      // allowlist stores the decoded DB value — compare both forms.
      let decodedPath = req.path;
      try {
        decodedPath = decodeURIComponent(req.path);
      } catch {
        /* malformed encoding → fall back to raw */
      }
      if (publicUploads.has(req.path) || publicUploads.has(decodedPath))
        return next(); // public branding
      const token =
        readCookie(req.headers.cookie, 'uploads_token') ||
        (req.headers.authorization?.startsWith('Bearer ')
          ? req.headers.authorization.slice(7)
          : null);
      if (token && jwtSecret) {
        try {
          const payload = jwtService.verify(token, { secret: jwtSecret }) as {
            twoFactorPending?: boolean;
          };
          if (!payload.twoFactorPending) return next();
        } catch {
          /* invalid/expired → 401 below */
        }
      }
      res
        .status(401)
        .json({ statusCode: 401, message: 'Authentication required for this file' });
    },
    express.static(uploadsDir),
  );

  // Enable CORS for frontend
  const allowedOrigins = process.env.CORS_ORIGINS
    ? process.env.CORS_ORIGINS.split(',').map((o) => o.trim())
    : [];
  app.enableCors({
    origin: (origin, callback) => {
      // Allow requests with no origin (server-to-server, mobile apps)
      if (!origin) return callback(null, true);
      // Allow localhost only outside production (dev tooling / local apps)
      if (
        process.env.NODE_ENV !== 'production' &&
        /^http:\/\/localhost(:\d+)?$/.test(origin)
      ) {
        return callback(null, true);
      }
      // Allow configured production origins
      if (allowedOrigins.includes(origin)) return callback(null, true);
      callback(new Error('Not allowed by CORS'));
    },
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    credentials: true,
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );

  // Global exception filter
  app.useGlobalFilters(new AllExceptionsFilter());

  // Global prefix for all API routes
  app.setGlobalPrefix('api');

  const port = process.env.PORT ?? 3001;
  await app.listen(port);
  logger.log(`iTour Backend running on http://localhost:${port}`);
}
bootstrap();
