export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    let message = text || res.statusText;
    try {
      const data = JSON.parse(text);
      if (typeof data.detail === "string") {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((d: { loc?: (string | number)[]; msg?: string }) =>
            d.loc && d.loc.length > 1 ? `${d.loc.slice(1).join(".")}: ${d.msg}` : d.msg,
          )
          .filter(Boolean)
          .join("；");
      }
    } catch {
      // 非 JSON 响应时保留原文
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
