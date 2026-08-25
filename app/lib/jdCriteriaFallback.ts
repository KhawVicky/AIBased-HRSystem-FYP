// Keeps JD criteria generation available when the remote model service is unavailable.
export interface CriteriaResponseShape {
  success?: unknown;
  data?: {
    criteria?: unknown;
    [key: string]: unknown;
  };
  error?: unknown;
  warnings?: unknown;
}

export interface CriteriaFallbackOptions {
  fallbackWarning: string;
  logger?: (message: string, details?: string) => void;
}

export function criteriaResponseError(response: unknown): string {
  if (!response || typeof response !== "object") {
    return "The criteria service returned an invalid response.";
  }

  const error = (response as CriteriaResponseShape).error;
  if (typeof error === "string" && error.trim() !== "") {
    return error.trim();
  }
  if (error && typeof error === "object") {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim() !== "") {
      return message.trim();
    }
  }

  return "The criteria service returned an unusable response.";
}

export function isUsableCriteriaResponse(
  response: unknown,
): response is CriteriaResponseShape & {
  success: true;
  data: { criteria: unknown[]; [key: string]: unknown };
} {
  if (!response || typeof response !== "object") return false;

  const payload = response as CriteriaResponseShape;
  return (
    payload.success === true &&
    Boolean(payload.data) &&
    Array.isArray(payload.data?.criteria)
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error && error.message.trim() !== ""
    ? error.message
    : "The criteria service request failed.";
}

/**
 * Tries the remote criteria service first and falls back to the local
 * rule-based service for transport failures and unusable response payloads.
 */
export async function withCriteriaFallback<T extends CriteriaResponseShape>(
  remoteRequest: () => Promise<unknown>,
  localRequest: () => Promise<unknown>,
  options: CriteriaFallbackOptions,
): Promise<T> {
  options.logger?.("RunPod request attempted");

  try {
    const remoteResponse = await remoteRequest();
    if (isUsableCriteriaResponse(remoteResponse)) {
      return remoteResponse as T;
    }

    options.logger?.(
      "RunPod failed",
      criteriaResponseError(remoteResponse),
    );
  } catch (error) {
    options.logger?.("RunPod failed", errorMessage(error));
  }

  options.logger?.("local fallback used");

  try {
    const localResponse = await localRequest();
    if (!isUsableCriteriaResponse(localResponse)) {
      throw new Error(criteriaResponseError(localResponse));
    }

    const warnings = Array.isArray(localResponse.warnings)
      ? localResponse.warnings.filter(
          (warning): warning is string => typeof warning === "string",
        )
      : [];

    return {
      ...localResponse,
      warnings: [options.fallbackWarning, ...warnings],
    } as T;
  } catch (error) {
    throw new Error(
      `Unable to generate JD criteria. RunPod was unavailable and the local rule-based fallback failed: ${errorMessage(error)}`,
    );
  }
}
