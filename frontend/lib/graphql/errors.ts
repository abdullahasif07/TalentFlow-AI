export function graphQLErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
) {
  if (!(error instanceof Error) || !error.message.trim()) return fallback;

  const message = error.message.trim();
  if (/failed to fetch|network request failed|load failed/i.test(message)) {
    return "We couldn’t reach the TalentFlow API. Check that the backend is running, then try again.";
  }
  if (/status (code )?5\d\d|internal server error/i.test(message)) {
    return "The TalentFlow API had a problem processing this request. Please try again.";
  }

  return message;
}
