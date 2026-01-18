import { WardRiskLatest } from "@/types/risk"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"


export async function apiFetch<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  })

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login"
    }
    throw new Error(`API error: ${res.status}`)
  }

  return res.json()
}

export async function fetchLatestWardRisk( hours: number = 24, threshold: number = 80): Promise<WardRiskLatest[]> {
  console.log("Fetching latest ward risk data from API")
  return apiFetch<WardRiskLatest[]>("/wards/latest/risk?hours=${hours}&threshold=${threshold}", { method: "GET" })
}

