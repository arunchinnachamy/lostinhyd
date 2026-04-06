/**
 * Auth middleware for all /api/* routes.
 * Validates Bearer token against ADMIN_TOKEN env var.
 * Skips auth for /api/auth/verify (the login endpoint).
 */
export const onRequest: PagesFunction<Env> = async (context) => {
  const url = new URL(context.request.url);

  // Skip auth for the verify endpoint (login check)
  if (url.pathname === "/api/auth/verify") {
    return context.next();
  }

  const authHeader = context.request.headers.get("Authorization");
  const token = authHeader?.startsWith("Bearer ")
    ? authHeader.slice(7)
    : null;

  if (!token || token !== context.env.ADMIN_TOKEN) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  return context.next();
};
