const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const TOKEN_KEY = "tracker-token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function errorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const candidate = body as {
    detail?: string | { message?: string };
    error?: { message?: string };
  };
  if (typeof candidate.detail === "string") return candidate.detail;
  if (candidate.detail?.message) return candidate.detail.message;
  if (candidate.error?.message) return candidate.error.message;
  return fallback;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) ?? {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 || res.status === 403) {
    setToken(null);
    window.location.href = "/login";
    throw new ApiError(res.status, "Nicht angemeldet");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = errorMessage(body, detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postIdempotent: <T>(path: string, idempotencyKey: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    }),
};

async function openAuthenticatedPdf(path: string, fileName: string) {
  const popup = window.open("about:blank", "_blank");
  if (popup) popup.opener = null;
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    popup?.close();
    throw new ApiError(res.status, "PDF konnte nicht geladen werden");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  if (popup) {
    popup.location.href = url;
  } else {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.setAttribute("aria-label", fileName);
    anchor.click();
  }
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export async function downloadAuthenticated(path: string, fileName: string) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = errorMessage(await res.json(), detail);
    } catch {
      /* response is not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export function openInvoicePdf(invoiceId: number, invoiceNumber: string) {
  return openAuthenticatedPdf(
    `/invoices/${invoiceId}/pdf`,
    `${invoiceNumber}.pdf`
  );
}

export function openQuotePdf(quoteId: number, quoteNumber: string) {
  return openAuthenticatedPdf(`/quotes/${quoteId}/pdf`, `${quoteNumber}.pdf`);
}

export async function uploadCompanyLogo<T>(file: File): Promise<T> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/settings/logo`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = errorMessage(body, detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchCompanyLogoUrl(): Promise<string | null> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/settings/logo`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new ApiError(res.status, "Logo konnte nicht geladen werden");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function uploadExpenseReceipt<T>(expenseId: number, file: File): Promise<T> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/expenses/${expenseId}/receipt`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = errorMessage(body, detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function openExpenseReceipt(expenseId: number) {
  const token = getToken();
  const res = await fetch(`${API_BASE}/expenses/${expenseId}/receipt`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Beleg konnte nicht geladen werden");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export { ApiError, API_BASE };
