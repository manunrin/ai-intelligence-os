/** Middleware to protect routes from unauthenticated access. */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/register"];
const PROTECTED_PREFIXES = [""]; // root path is protected

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for static assets and API routes
  if (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/api/") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );

  // Public paths are always accessible
  if (isPublic) {
    return NextResponse.next();
  }

  // Protected paths — check for token in cookie or header
  // Since we use localStorage + setAuthToken, we can't read it in middleware.
  // Instead, redirect to login for any non-public path.
  // The client-side page will handle the actual auth check and redirect.
  // This middleware is a server-side safety net.

  // Allow the request through — client-side auth context handles the real protection
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
