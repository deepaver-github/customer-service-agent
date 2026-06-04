import { Injectable, computed, inject, signal } from '@angular/core';
import { AuthService, AuthUser } from './auth.service';

export type UserRole = 'staff' | 'participant';

export interface CurrentUser {
  id: string;
  email: string;
  role: string;
  staffId: string | null;
  participantId: string | null;
  name: string;
  initials: string;
  roleLabel: string;
  isStaff: boolean;
}

interface StoredSession {
  token: string;
  user: AuthUser;
  expiresAt: string;
}

const STORAGE_KEY = 'sca-auth';

const STAFF_ROLES = new Set(['admin', 'manager', 'coordinator', 'support_worker']);

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrator',
  manager: 'Manager',
  coordinator: 'Coordinator',
  support_worker: 'Support worker',
  participant: 'Participant',
};

function loadFromStorage(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    if (!parsed.token || !parsed.user) return null;
    if (parsed.expiresAt && new Date(parsed.expiresAt).getTime() <= Date.now()) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function deriveInitials(name: string, email: string): string {
  const source = name?.trim() || email.split('@')[0] || 'U';
  const parts = source.replace(/[._-]+/g, ' ').trim().split(/\s+/);
  const first = parts[0]?.[0] ?? 'U';
  const second = parts[1]?.[0] ?? (parts[0]?.[1] ?? '');
  return (first + second).toUpperCase().slice(0, 2);
}

function deriveName(email: string): string {
  const local = email.split('@')[0] || 'User';
  return local
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function toCurrent(user: AuthUser): CurrentUser {
  const name = user.name?.trim() || deriveName(user.email);
  return {
    id: user.id,
    email: user.email,
    role: user.role,
    staffId: user.staff_id,
    participantId: user.participant_id,
    name,
    initials: deriveInitials(name, user.email),
    roleLabel: ROLE_LABELS[user.role] || user.role,
    isStaff: STAFF_ROLES.has(user.role),
  };
}

@Injectable({ providedIn: 'root' })
export class AuthStore {
  private authApi = inject(AuthService);

  private readonly session = signal<StoredSession | null>(loadFromStorage());

  readonly currentUser = computed(() => {
    const s = this.session();
    return s ? toCurrent(s.user) : null;
  });

  readonly isAuthenticated = computed(() => this.session() !== null);

  tokenSnapshot(): string | null {
    return this.session()?.token ?? null;
  }

  async signIn(email: string, password: string): Promise<CurrentUser> {
    const res = await this.authApi.login(email, password);
    const stored: StoredSession = {
      token: res.token,
      user: res.user,
      expiresAt: res.expires_at,
    };
    this.session.set(stored);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch {}
    return toCurrent(res.user);
  }

  async signOut(): Promise<void> {
    try {
      await this.authApi.logout();
    } catch {
      // Best-effort — clear local state even if the server call fails.
    }
    this.clear();
  }

  clear(): void {
    this.session.set(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }
}
