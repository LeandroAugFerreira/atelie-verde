let token = sessionStorage.getItem("greenscape-token") || "";
export function setToken(value: string) {
  token = value;
  value
    ? sessionStorage.setItem("greenscape-token", value)
    : sessionStorage.removeItem("greenscape-token");
}
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  const requestToken = token;
  try {
    response = await fetch("/api" + path, { ...options, headers });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(
      "Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.",
      0,
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (
      response.status === 401 &&
      requestToken &&
      token === requestToken &&
      path !== "/auth/login"
    ) {
      setToken("");
      window.dispatchEvent(new Event("atelie-session-expired"));
    }
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.[0]?.msg ||
            "Não foi possível concluir. Verifique a conexão com a API.",
      response.status,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export async function imageBlob(url: string) {
  if (!/^\/api\/images\/\d+\/content$/.test(url))
    throw new ApiError("Endereço da imagem inválido.", 422);
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Imagem indisponível");
  return URL.createObjectURL(await res.blob());
}

export async function assistantPhoto(url: string) {
  if (!/^\/api\/assistant\/attachments\/\d+\/content$/.test(url))
    throw new ApiError("Foto inválida.", 422);
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok)
    throw new ApiError("Não foi possível abrir a foto.", response.status);
  return URL.createObjectURL(await response.blob());
}
export const write = <T>(path: string, body: unknown, method = "POST") =>
  api<T>(path, { method, body: JSON.stringify(body) });
