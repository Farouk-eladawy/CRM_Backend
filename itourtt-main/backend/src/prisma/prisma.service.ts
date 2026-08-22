import { Injectable, OnModuleInit, OnModuleDestroy, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PrismaClient } from '../../generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';

const SLOW_QUERY_THRESHOLD_MS = 1000;

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger('PrismaSlowQuery');
  private pool: pg.Pool;

  constructor(configService: ConfigService) {
    const pool = new pg.Pool({
      connectionString: configService.get<string>('DATABASE_URL'),
      max: 20,
      min: 5,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    const adapter = new PrismaPg(pool);
    super({ adapter, log: [{ level: 'query', emit: 'event' }] } as any);
    this.pool = pool;
  }

  async onModuleInit() {
    await this.$connect();
    (this as any).$on('query', (e: { query: string; duration: number }) => {
      if (e.duration >= SLOW_QUERY_THRESHOLD_MS) {
        this.logger.warn(`Slow query (${e.duration}ms): ${e.query.slice(0, 200)}`);
      }
    });
  }

  async onModuleDestroy() {
    await this.$disconnect();
    await this.pool.end();
  }
}
