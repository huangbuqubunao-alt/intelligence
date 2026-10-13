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
  let body: T & { error?: ApiError };
  try {
    body = (await response.json()) as T & { error?: ApiError };
  } catch (reason) {
    // A read can be requested again explicitly; a mutation may already have
    // executed and must retain its uncertain failure without replay or remapping.
    if (!["GET", "HEAD"].includes((options.method ?? "GET").toUpperCase())) throw reason;
    throw new ApiRequestError({
      code: response.status >= 500 ? "READ_SERVICE_UNAVAILABLE" : "READ_RESPONSE_INVALID",
      message: reason instanceof Error ? reason.message : "The local service response could not be read.",
    });
  }
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

/** Browser-owned File: actual large-upload bytes without an ArrayBuffer copy. */
export async function uploadLocal<T>(path: string, file: File, signal: AbortSignal,
  onProgress: (loaded: number, total: number) => void, onVerifying: () => void): Promise<T> {
  if (file.size <= 64 * 1024 * 1024) {
    return api<T>(path, { method: "POST", body: file, signal, headers: { "Content-Type": "application/octet-stream" } });
  }
  return new Promise<T>((resolve, reject) => {
    const request = new XMLHttpRequest();
    const abort = () => request.abort();
    const cleanup = () => signal.removeEventListener("abort", abort);
    request.open("POST", `/api/v1${path}`);
    request.timeout = 2 * 60 * 60 * 1000 + 5 * 60 * 1000;
    request.setRequestHeader("Accept", "application/json");
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.setRequestHeader("X-YIA-Request", "local-ui");
    request.upload.onprogress = event => { if (event.lengthComputable) onProgress(event.loaded, event.total); };
    request.upload.onload = onVerifying;
    request.onload = () => {
      cleanup();
      try {
        const body = JSON.parse(request.responseText) as T & { error?: ApiError };
        if (request.status >= 200 && request.status < 300) resolve(body);
        else reject(new ApiRequestError(body.error ?? { code: "REQUEST_REJECTED", message: "The local service rejected this request." }));
      } catch (error) { reject(error); }
    };
    request.onerror = () => { cleanup(); reject(new ApiRequestError({ code: "LOCAL_IMPORT_INTERRUPTED", message: "Local connection was interrupted." })); };
    request.ontimeout = () => { cleanup(); reject(new ApiRequestError({ code: "LOCAL_IMPORT_TIMEOUT", message: "Local import timed out." })); };
    request.onabort = () => { cleanup(); reject(new ApiRequestError({ code: "LOCAL_IMPORT_CANCELLED", message: "Import was cancelled." })); };
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) { cleanup(); reject(new ApiRequestError({ code: "LOCAL_IMPORT_CANCELLED", message: "Import was cancelled." })); return; }
    request.send(file);
  });
}
