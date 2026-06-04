import { HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthStore } from './auth.store';

const AUTH_SKIP_PATHS = ['/auth/login', '/health'];

function shouldAttach(url: string): boolean {
  return !AUTH_SKIP_PATHS.some((p) => url.startsWith(p) || url.includes(p));
}

export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const auth = inject(AuthStore);
  const router = inject(Router);

  let outgoing = req;
  const token = auth.tokenSnapshot();
  if (token && shouldAttach(req.url)) {
    outgoing = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  return next(outgoing).pipe(
    catchError((err) => {
      if (err?.status === 401 && !req.url.includes('/auth/login')) {
        auth.clear();
        router.navigate(['/login'], { queryParams: { reason: 'expired' } });
      }
      return throwError(() => err);
    }),
  );
};
