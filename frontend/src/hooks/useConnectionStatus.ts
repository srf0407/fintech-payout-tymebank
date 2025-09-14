/**
 * Hook for tracking connection status and network state.
 * Integrates with retry service to provide connection information.
 */

import { useState, useEffect, useCallback } from 'react';
import { retryService, RETRY_CONFIGS } from '../utils/retryService';

export interface ConnectionStatus {
  isOnline: boolean;
  isRetrying: boolean;
  retryCount: number;
  lastError: string | null;
  lastSuccess: Date | null;
}

export interface UseConnectionStatusReturn {
  status: ConnectionStatus;
  testConnection: () => Promise<boolean>;
  resetStatus: () => void;
}

export const useConnectionStatus = (): UseConnectionStatusReturn => {
  const [status, setStatus] = useState<ConnectionStatus>({
    isOnline: navigator.onLine,
    isRetrying: false,
    retryCount: 0,
    lastError: null,
    lastSuccess: null,
  });

  // Listen for online/offline events
  useEffect(() => {
    const handleOnline = () => {
      setStatus(prev => ({
        ...prev,
        isOnline: true,
        lastError: null,
      }));
    };

    const handleOffline = () => {
      setStatus(prev => ({
        ...prev,
        isOnline: false,
        lastError: 'Network connection lost',
      }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const testConnection = useCallback(async (): Promise<boolean> => {
    if (!navigator.onLine) {
      setStatus(prev => ({
        ...prev,
        isOnline: false,
        lastError: 'No network connection',
      }));
      return false;
    }

    setStatus(prev => ({
      ...prev,
      isRetrying: true,
    }));

    try {
      // Test connection with a simple fetch to the backend
      const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
      
      const result = await retryService.retry(
        async () => {
          // Try health endpoint first (doesn't require auth)
          const healthResponse = await fetch(`${baseUrl}/health`, {
            method: 'HEAD',
            signal: AbortSignal.timeout(3000)
          });
          
          if (healthResponse.ok) {
            return true;
          }
          
          // If health endpoint fails, try auth endpoint
          const authResponse = await fetch(`${baseUrl}/auth/me`, {
            method: 'HEAD',
            credentials: 'include',
            signal: AbortSignal.timeout(3000)
          });
          
          if (!authResponse.ok && authResponse.status !== 401) {
            throw new Error(`HTTP ${authResponse.status}`);
          }
          
          return true;
        },
        RETRY_CONFIGS.HEALTH_CHECK,
        'connection-test'
      );

      if (result.success) {
        setStatus(prev => ({
          ...prev,
          isOnline: true,
          isRetrying: false,
          retryCount: 0,
          lastError: null,
          lastSuccess: new Date(),
        }));
        return true;
      } else {
        setStatus(prev => ({
          ...prev,
          isOnline: false,
          isRetrying: false,
          retryCount: prev.retryCount + 1,
          lastError: result.error?.message || 'Connection test failed',
        }));
        return false;
      }
    } catch (error) {
      setStatus(prev => ({
        ...prev,
        isOnline: false,
        isRetrying: false,
        retryCount: prev.retryCount + 1,
        lastError: error instanceof Error ? error.message : 'Unknown error',
      }));
      return false;
    }
  }, []);

  const resetStatus = useCallback(() => {
    setStatus({
      isOnline: navigator.onLine,
      isRetrying: false,
      retryCount: 0,
      lastError: null,
      lastSuccess: null,
    });
  }, []);

  return {
    status,
    testConnection,
    resetStatus,
  };
};
