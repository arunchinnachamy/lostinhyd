/**
 * POST /api/auth/verify
 * Validates the provided token against ADMIN_TOKEN.
 * Used by the React Admin authProvider during login.
 */
export const onRequestPost: PagesFunction<Env> = async (context) => {
  try {
    const body = (await context.request.json()) as { token?: string };

    if (!body.token) {
      return Response.json({ error: "Token is required" }, { status: 400 });
    }

    if (body.token !== context.env.ADMIN_TOKEN) {
      return Response.json({ error: "Invalid token" }, { status: 401 });
    }

    return Response.json({ ok: true });
  } catch {
    return Response.json({ error: "Invalid request body" }, { status: 400 });
  }
};
