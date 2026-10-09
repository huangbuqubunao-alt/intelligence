export type ApiError = {
  code: string;
  message: string;
  /** Optional machine-readable context for localized UI copy. */
  details?: { reason_code?: string | null; availability?: string; consent_required?: boolean };
};

/** An API failure that keeps its machine code so callers can localize by code. */
export class ApiRequestError extends Error {
  readonly code: string;
  readonly technicalMessage: string;
  readonly details?: ApiError["details"];
  constructor(error: ApiError) {
    super(error.code === "VALIDATION_ERROR" ? "The request could not be accepted. Check the entered information and try again." : error.message);
    this.technicalMessage = error.message;
    this.name = "ApiRequestError";
    this.code = error.code;
    this.details = error.details;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json", "X-YIA-Request": "local-ui" } : {}),
      ...options.headers
    }
  });
  const body = (await response.json()) as T & { error?: ApiError };
  if (!response.ok) throw new ApiRequestError(body.error ?? { code: "REQUEST_REJECTED", message: "The local service rejected this request." });
  return body;
}

export const post = <T>(path: string, body: object) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export async function uploadZip<T>(path: string, file: File): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: "POST",
    body: file,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/zip",
      "X-YIA-Request": "local-ui",
    },
  });
  const body = (await response.json()) as T & { error?: ApiError };
  if (!response.ok) {
    throw new Error(body.error?.message ?? "The local service rejected this backup.");
  }
  return body;
}
export const patch = <T>(path: string, body: object) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const put = <T>(path: string, body: object) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
