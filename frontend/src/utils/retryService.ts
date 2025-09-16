/**
 * Frontend retry service for handling transient API errors.
 * Integrates with backend error responses and implements smart retry logic.
 */

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  exponentialBase: number;
  jitter: boolean;
}

export interface BackendErrorResponse {
  error: string;
  message: string;
  correlation_id?: string;
  retry_after?: number;
  details?: Record<string, any>;
}

export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: Error;
  attempts: number;
  finalError?: BackendErrorResponse;
}

class RetryService {
  private readonly DEFAULT_CONFIG: RetryConfig = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 30000, 
    exponentialBase: 2,
    jitter: true,
  };

  /**
   * Check if an error is retryable based on HTTP status and backend error codes
   */
  private isRetryableError(error: any): boolean {
    // Check if it's a fetch error (network issues) 
    if (error instanceof TypeError && error.message.includes('fetch')) {
      if (error.message.includes('Failed to fetch')) {
        return false;
      }
      return true;
    }

    // Check for specific network error types
    if (error.message && (
      error.message.includes('ERR_CONNECTION_REFUSED') ||
      error.message.includes('ERR_NETWORK_CHANGED') ||
      error.message.includes('ERR_INTERNET_DISCONNECTED') ||
      error.message.includes('ERR_CONNECTION_TIMED_OUT') ||     
     // error.message.includes('NetworkError') || originally included picked up in code review *incorrect*
      error.message.includes('connection')
    )) {
      return true;
    }

    // Check if it's an HTTP error with status code
    if (error.status) {
      const retryableStatusCodes = [429, 500, 502, 503, 504, 408];
      return retryableStatusCodes.includes(error.status);
    }

    // Check if it's a backend error response
    if (error.error) {
      const retryableErrorCodes = [
        'rate_limit_exceeded',
        'database_connection_error',
        'external_service_unavailable',
        'payment_provider_error',
        'internal_server_error',
        'service_unavailable',
      ];
      return retryableErrorCodes.includes(error.error);
    }

    return false;
  }

  /**
   * Check if an error indicates backend is down
   */
  public isBackendDownError(error: any): boolean {
    // Network errors that indicate backend is down
    if (error.message && (
      error.message.includes('ERR_CONNECTION_REFUSED') ||
      error.message.includes('Failed to fetch') ||
      error.message.includes('NetworkError')
    )) {
      return true;
    }

    // HTTP status codes that indicate backend issues
    if (error.status && [502, 503, 504].includes(error.status)) {
      return true;
    }

    // Backend error codes that indicate service issues
    if (error.error && [
      'database_connection_error',
      'external_service_unavailable',
      'service_unavailable'
    ].includes(error.error)) {
      return true;
    }

    return false;
  }

  /**
   * Extract backend error response from fetch error
   */
  private async extractBackendError(response: Response): Promise<BackendErrorResponse | null> {
    try {
      const errorData = await response.json();
      if (errorData.error && errorData.message) {
        return errorData as BackendErrorResponse;
      }
    } catch {
      // If we can't parse JSON, return null
    }
    return null;
  }

  /**
   * Check if backend is reachable
   */
  async checkBackendHealth(baseUrl: string): Promise<boolean> {
    try {
      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000) 
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * Calculate delay with exponential backoff and jitter
   */
  private calculateDelay(attempt: number, config: RetryConfig, retryAfter?: number): number {
    if (retryAfter) {
      return retryAfter * 1000;
    }


    let delay = config.baseDelay * Math.pow(config.exponentialBase, attempt);
    delay = Math.min(delay, config.maxDelay);

    if (config.jitter) {
      const jitterFactor = 0.5 + Math.random() * 0.5; 
      delay *= jitterFactor;
    }

    return delay;
  }

  /**
   * Sleep for specified milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Retry an async function with smart error handling
   */
  async retry<T>(
    fn: () => Promise<T>,
    config: Partial<RetryConfig> = {},
    correlationId?: string
  ): Promise<RetryResult<T>> {
    const finalConfig = { ...this.DEFAULT_CONFIG, ...config };
    let lastError: any;
    let backendError: BackendErrorResponse | null = null;

    for (let attempt = 0; attempt <= finalConfig.maxRetries; attempt++) {
      try {
        const result = await fn();
        
        if (attempt > 0) {
          console.log(`Retry successful after ${attempt} attempts`, {
            correlationId,
            attempts: attempt + 1,
          });
        }

        return {
          success: true,
          data: result,
          attempts: attempt + 1,
        };
      } catch (error: any) {
        lastError = error;

        if (error.response) {
          backendError = await this.extractBackendError(error.response);
        }
        if (!this.isRetryableError(error)) {
          console.warn('Non-retryable error encountered', {
            correlationId,
            error: error.message || error,
            attempt: attempt + 1,
          });
          
          let finalError = error;
          if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            finalError = new Error('Server is currently unavailable. Please try again later.');
          }
          
          return {
            success: false,
            error: finalError,
            attempts: attempt + 1,
            finalError: backendError || undefined,
          };
        }

        if (attempt === finalConfig.maxRetries) {
          console.error('All retry attempts exhausted', {
            correlationId,
            attempts: attempt + 1,
            error: error.message || error,
            backendError,
          });

          let finalError = error;
          if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            finalError = new Error('Server is currently unavailable. Please try again later.');
          }

          return {
            success: false,
            error: finalError,
            attempts: attempt + 1,
            finalError: backendError || undefined,
          };
        }

        const delay = this.calculateDelay(
          attempt,
          finalConfig,
          backendError?.retry_after
        );

        console.warn('Retryable error encountered, retrying', {
          correlationId,
          attempt: attempt + 1,
          maxRetries: finalConfig.maxRetries,
          error: error.message || error,
          backendError: backendError?.error,
          delayMs: delay,
        });

        await this.sleep(delay);
      }
    }

    return {
      success: false,
      error: lastError,
      attempts: finalConfig.maxRetries + 1,
      finalError: backendError || undefined,
    };
  }

  /**
   * Create a retry wrapper for fetch requests
   */
  async retryFetch(
    url: string,
    options: RequestInit = {},
    config: Partial<RetryConfig> = {},
    correlationId?: string
  ): Promise<Response> {
    const result = await this.retry(
      async () => {
        const response = await fetch(url, options);
        
        if (!response.ok) {
          const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
          (error as any).status = response.status;
          (error as any).response = response;
          throw error;
        }
        
        return response;
      },
      config,
      correlationId
    );

    if (!result.success) {
      throw result.error;
    }

    return result.data!;
  }
}

// Export singleton instance
export const retryService = new RetryService();

// Predefined configurations for different scenarios
export const RETRY_CONFIGS = {
  // Quick retry for user-initiated actions
  QUICK: {
    maxRetries: 2,
    baseDelay: 500,
    maxDelay: 2000,
    exponentialBase: 2,
    jitter: true,
  },
  
  // Standard retry for most API calls
  STANDARD: {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    exponentialBase: 2,
    jitter: true,
  },
  
  // Aggressive retry for critical operations
  AGGRESSIVE: {
    maxRetries: 5,
    baseDelay: 1000,
    maxDelay: 30000,
    exponentialBase: 2,
    jitter: true,
  },
  
  // Conservative retry for background operations
  CONSERVATIVE: {
    maxRetries: 2,
    baseDelay: 2000,
    maxDelay: 15000,
    exponentialBase: 2,
    jitter: true,
  },
  
  // Health check retry for backend connectivity tests
  HEALTH_CHECK: {
    maxRetries: 1,
    baseDelay: 1000,
    maxDelay: 3000,
    exponentialBase: 1,
    jitter: false,
  },
  
  // Fast fail for when backend is detected as down
  BACKEND_DOWN: {
    maxRetries: 1,
    baseDelay: 0,
    maxDelay: 0,
    exponentialBase: 2,
    jitter: false,
  },
} as const;

// Export error detection utilities
export const isBackendDownError = (error: any): boolean => {
  return retryService.isBackendDownError(error);
};
