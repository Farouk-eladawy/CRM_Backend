import { IsNotEmpty, IsString, IsIn } from 'class-validator';

export class RegisterDeviceTokenDto {
  @IsString()
  @IsNotEmpty()
  token!: string;

  @IsString()
  @IsIn(['ios', 'android'])
  platform!: string;
}

export class RemoveDeviceTokenDto {
  @IsString()
  @IsNotEmpty()
  token!: string;
}
