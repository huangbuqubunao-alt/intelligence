export function apiProxyTarget(value?: string): string {
  return value ?? "http://127.0.0.1:8765";
}
