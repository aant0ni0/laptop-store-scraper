export class ApiRequestError extends Error {
  constructor(status) {
    super(`API request failed with status ${status}`);
    this.status = status;
  }
}

export async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiRequestError(response.status);
  }
  return response.json();
}
