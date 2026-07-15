const API_BASE = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? "" : "http://localhost:5000")

if (!API_BASE && import.meta.env.PROD) {
  console.error("VITE_API_BASE_URL is not set — API calls will fail")
}

export interface ApiError {
  error: string
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ error: resp.statusText }))
    throw new Error(body.error || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal): Promise<T> =>
    fetch(`${API_BASE}${path}`, { signal, credentials: "include" }).then(handleResponse<T>),

  post: <T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> =>
    fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
      credentials: "include",
    }).then(handleResponse<T>),
}
