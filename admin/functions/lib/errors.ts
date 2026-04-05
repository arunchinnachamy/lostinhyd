/**
 * Shared error handler for API functions.
 * Maps database and validation errors to structured JSON responses.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function notFound(resource: string): ApiError {
  return new ApiError(`${resource} not found`, 404);
}

export function badRequest(message: string, details?: unknown): ApiError {
  return new ApiError(message, 400, details);
}

/**
 * Wrap a handler function with error handling.
 * Catches ApiError for structured responses, pg errors for DB issues.
 */
export function handleError(error: unknown): Response {
  if (error instanceof ApiError) {
    return Response.json(
      { error: error.message, details: error.details },
      { status: error.status },
    );
  }

  const pgError = error as { code?: string; message?: string };

  // PostgreSQL unique violation
  if (pgError.code === "23505") {
    return Response.json(
      { error: "Duplicate entry", details: pgError.message },
      { status: 409 },
    );
  }

  // PostgreSQL foreign key violation
  if (pgError.code === "23503") {
    return Response.json(
      { error: "Referenced record not found", details: pgError.message },
      { status: 400 },
    );
  }

  console.error("Unhandled API error:", error);
  return Response.json(
    { error: "Internal server error" },
    { status: 500 },
  );
}
