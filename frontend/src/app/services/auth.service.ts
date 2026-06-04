import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  staff_id: string | null;
  participant_id: string | null;
  name: string | null;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
  user: AuthUser;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);

  login(email: string, password: string): Promise<LoginResponse> {
    return firstValueFrom(
      this.http.post<LoginResponse>('/auth/login', { email, password }),
    );
  }

  me(): Promise<AuthUser> {
    return firstValueFrom(this.http.get<AuthUser>('/auth/me'));
  }

  logout(): Promise<void> {
    return firstValueFrom(this.http.post<void>('/auth/logout', {}));
  }
}
