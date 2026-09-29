const credentials = btoa("ana:ana123");

export async function getSurveyResults(surveyId, filters = {}) {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  const query = params.toString() ? `?${params}` : "";

  const response = await fetch(`/api/surveys/${surveyId}/results/${query}`, {
    headers: { Authorization: `Basic ${credentials}` },
  });

  if (response.status === 400) {
    const errors = await response.json();
    throw new Error(
      Object.entries(errors)
        .map(([field, messages]) => `${field}: ${messages.join(" ")}`)
        .join(" "),
    );
  }

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

