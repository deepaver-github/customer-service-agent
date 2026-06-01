import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import {
  SessionDetail,
  SessionListResponse,
} from '../models/session.model';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private http = inject(HttpClient);

  list(cursor?: string | null, limit = 30): Promise<SessionListResponse> {
    let params = new HttpParams().set('limit', String(limit));
    if (cursor) params = params.set('cursor', cursor);
    return firstValueFrom(this.http.get<SessionListResponse>('/sessions', { params }));
  }

  get(sessionId: string): Promise<SessionDetail> {
    return firstValueFrom(this.http.get<SessionDetail>(`/sessions/${sessionId}`));
  }

  close(sessionId: string): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/sessions/${sessionId}`));
  }
}
