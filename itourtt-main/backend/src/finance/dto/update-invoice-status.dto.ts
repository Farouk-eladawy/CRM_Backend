import { IsString, IsIn } from 'class-validator';

export class UpdateInvoiceStatusDto {
  @IsString()
  @IsIn(['POSTED', 'CANCELLED'])
  status!: string;
}
