import { useState, useCallback, useRef } from 'react';

export interface ErrorState {
  error: string | null;
  correlationId?: string;
  timestamp?: Date;
}

export interface ErrorHandlerReturn {
  error: ErrorState | null;
  handleError: (error: Error | string, correlationId?: string) => void;
  clearError: () => void;
  hasError: boolean;
}

/**
 * Centralized error handling hook
 * Provides consistent error state management across components
 */
export const useErrorHandler = (): ErrorHandlerReturn => {
  const [error, setError] = useState<ErrorState | null>(null);
  const errorTimeoutRef = useRef<number | null>(null);  
  
  const handleError = useCallback((error: Error | string, correlationId?: string) => {
    // Clear any existing timeout
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
    }

    const errorMessage = error instanceof Error ? error.message : error;
    
    setError({
      error: errorMessage,
      correlationId,
      timestamp: new Date(),
    });

    // Log error for monitoring
    console.error('Error handled:', {
      message: errorMessage,
      correlationId,
      timestamp: new Date().toISOString(),
      stack: error instanceof Error ? error.stack : undefined,
    });

    // Auto-clear error after 10 seconds
    errorTimeoutRef.current = setTimeout(() => {
      setError(null);
    }, 10000);
  }, []);

  const clearError = useCallback(() => {
    if (errorTimeoutRef.current) {
      clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = null;
    }
    setError(null);
  }, []);

  return {
    error,
    handleError,
    clearError,
    hasError: error !== null,
  };
};
