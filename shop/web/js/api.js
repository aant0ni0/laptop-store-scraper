export class ApiRequestError extends Error {
  constructor(status, retryAfterSeconds) {
    super(`API request failed with status ${status}`);
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const retryAfterSeconds = Number.parseInt(response.headers.get("Retry-After"), 10);
    throw new ApiRequestError(response.status, Number.isNaN(retryAfterSeconds) ? null : retryAfterSeconds);
  }
  return response.json();
}

export function requestErrorMessage(error, fallbackMessage) {
  if (error.status !== 429) {
    return fallbackMessage;
  }
  const retryHint = error.retryAfterSeconds ? `za ${error.retryAfterSeconds} s` : "za chwilę";
  return `Zbyt wiele zapytań. Spróbuj ponownie ${retryHint}.`;
}
