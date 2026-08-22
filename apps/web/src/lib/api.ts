export async function apiRequest<T>(path: string, token: string): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_CCM_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("CCM API base URL is not configured");
  }
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(`CCM API request rejected with status ${response.status}`);
  }
  return (await response.json()) as T;
}
