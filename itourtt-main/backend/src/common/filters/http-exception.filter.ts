import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Response } from 'express';
import { Prisma } from '../../../generated/prisma/client.js';

@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger('ExceptionFilter');

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    let status: number;
    let message: string | object;

    if (exception instanceof Prisma.PrismaClientKnownRequestError) {
      // Handle known Prisma errors
      switch (exception.code) {
        case 'P2002': {
          // Unique constraint violation
          const fields = (exception.meta?.target as string[]) || [];
          status = HttpStatus.CONFLICT;
          message = `A record with this ${fields.join(', ')} already exists`;
          break;
        }
        case 'P2003': {
          // Foreign key constraint violation
          status = HttpStatus.BAD_REQUEST;
          message = 'Related record not found';
          break;
        }
        case 'P2025': {
          // Record not found
          status = HttpStatus.NOT_FOUND;
          message = 'Record not found';
          break;
        }
        default: {
          status = HttpStatus.BAD_REQUEST;
          // Don't surface raw Prisma internals (schema/constraint/query
          // details) to clients in production; the full error is still logged.
          message =
            process.env.NODE_ENV === 'production'
              ? 'Invalid request'
              : exception.message;
        }
      }
    } else if (exception instanceof HttpException) {
      status = exception.getStatus();
      const res = exception.getResponse();
      message = typeof res === 'string' ? res : (res as any).message || res;
    } else {
      status = HttpStatus.INTERNAL_SERVER_ERROR;
      message = 'Internal server error';
    }

    this.logger.error(
      `Status: ${status} Error: ${JSON.stringify(message)}`,
      exception instanceof Error ? exception.stack : '',
    );

    response.status(status).json({
      statusCode: status,
      message,
      timestamp: new Date().toISOString(),
    });
  }
}
