import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  DashboardStats,
  KnowledgeListItem,
  ParticipantCreatePayload,
  ParticipantDetail,
  ParticipantListResponse,
  ParticipantUpdatePayload,
  StaffListItem,
} from '../models/participant.model';

@Injectable({ providedIn: 'root' })
export class ParticipantService {
  private http = inject(HttpClient);

  create(payload: ParticipantCreatePayload): Promise<ParticipantDetail> {
    return firstValueFrom(this.http.post<ParticipantDetail>('/participants', payload));
  }

  update(id: string, payload: ParticipantUpdatePayload): Promise<ParticipantDetail> {
    return firstValueFrom(this.http.patch<ParticipantDetail>(`/participants/${id}`, payload));
  }

  list(opts: { search?: string; status?: string; limit?: number } = {}): Promise<ParticipantListResponse> {
    let params = new HttpParams();
    if (opts.search) params = params.set('search', opts.search);
    if (opts.status) params = params.set('status', opts.status);
    if (opts.limit !== undefined) params = params.set('limit', String(opts.limit));
    return firstValueFrom(this.http.get<ParticipantListResponse>('/participants', { params }));
  }

  get(id: string): Promise<ParticipantDetail> {
    return firstValueFrom(this.http.get<ParticipantDetail>(`/participants/${id}`));
  }

  staff(): Promise<StaffListItem[]> {
    return firstValueFrom(this.http.get<StaffListItem[]>('/staff'));
  }

  knowledge(): Promise<KnowledgeListItem[]> {
    return firstValueFrom(this.http.get<KnowledgeListItem[]>('/knowledge'));
  }

  dashboardStats(): Promise<DashboardStats> {
    return firstValueFrom(this.http.get<DashboardStats>('/dashboard/stats'));
  }
}
