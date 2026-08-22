import { IsNotEmpty, IsIn } from 'class-validator';

export class UpdateStatusDto {
  @IsNotEmpty()
  @IsIn(['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW'])
  status!: 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';
}
