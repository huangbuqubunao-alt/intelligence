export type ApiError = { code: string; message: string };

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
  if (!response.ok) throw new Error(body.error?.message ?? "The local service rejected this request.");
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
