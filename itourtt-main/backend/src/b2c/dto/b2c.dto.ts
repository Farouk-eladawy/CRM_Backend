import { IsEmail, IsString, IsNotEmpty, IsInt, Min, IsOptional, IsDateString, Matches } from 'class-validator';

export class B2CLoginDto {
  @IsEmail()
  email!: string;

  @IsString()
  @IsNotEmpty()
  phone!: string;
}

export class B2CChangePasswordDto {
  @IsString()
  @IsNotEmpty()
  currentPassword!: string;

  @IsString()
  @IsNotEmpty()
  newPassword!: string;
}

export class B2CForgotPasswordDto {
  @IsEmail()
  email!: string;
}

export class B2CResetPasswordDto {
  @IsEmail()
  email!: string;

  @IsString()
  @IsNotEmpty()
  token!: string;

  @IsString()
  @IsNotEmpty()
  newPassword!: string;
}

export class B2CAmendBookingDto {
  @IsOptional()
  @IsDateString()
  @Matches(/^[2-9]\d{3}-/, { message: 'jobDate year must be 2000 or later' })
  jobDate?: string;

  @IsOptional()
  @IsString()
  pickupTime?: string;

  @IsOptional()
  @IsInt()
  @Min(1)
  paxCount?: number;
}
