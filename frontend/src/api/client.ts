export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseError(text) || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function parseError(text: string): string {
  if (!text) return "";
  try {
    const body = JSON.parse(text);
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (first?.msg) {
        const loc = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : "";
        return loc ? `${loc}：${first.msg}` : first.msg;
      }
    }
    return text;
  } catch {
    return text;
  }
}
