/**
 * Shared error handler for API routes.
 * Maps database and validation errors to structured JSON responses.
 */

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export function notFound(resource) {
  return new ApiError(`${resource} not found`, 404);
}

export function badRequest(message, details) {
  return new ApiError(message, 400, details);
}

/**
 * Express error handler middleware.
 */
export function handleError(error, req, res, next) {
  if (error instanceof ApiError) {
    return res.status(error.status).json({
      error: error.message,
      details: error.details,
    });
  }

  // PostgreSQL unique violation
  if (error.code === "23505") {
    return res.status(409).json({
      error: "Duplicate entry",
      details: error.message,
    });
  }

  // PostgreSQL foreign key violation
  if (error.code === "23503") {
    return res.status(400).json({
      error: "Referenced record not found",
      details: error.message,
    });
  }

  console.error("Unhandled API error:", error);
  return res.status(500).json({
    error: "Internal server error",
  });
}
