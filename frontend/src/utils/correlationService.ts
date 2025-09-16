/**
 * Correlation ID service for generating and managing request correlation IDs.
 * Generates unique UUIDs for each API request to enable end-to-end tracing.
 */

/**
 * Generate a UUID correlation ID
 */
export const generateCorrelationId = (): string => {
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
		/[xy]/g,
		function (c) {
			const r = (Math.random() * 16) | 0;
			const v = c === "x" ? r : (r & 0x3) | 0x8;
			return v.toString(16);
		}
	);
};

/**
 * Create headers object with correlation ID
 */
export const createHeadersWithCorrelationId = (
	additionalHeaders: Record<string, string> = {}
): Record<string, string> => {
	return {
		"Content-Type": "application/json",
		"X-Correlation-ID": generateCorrelationId(),
		...additionalHeaders,
	};
};

