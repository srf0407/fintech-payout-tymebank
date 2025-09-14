/**
 * Connection status indicator component.
 * Shows current connection state and retry information.
 */

import React, { useState, useEffect } from 'react';
import { Box, Chip, Typography, Button, Alert } from '@mui/material';
import { 
  Wifi, 
  WifiOff, 
  Refresh, 
  CheckCircle, 
  Error as ErrorIcon 
} from '@mui/icons-material';

export interface ConnectionStatusProps {
  isOnline?: boolean;
  isRetrying?: boolean;
  retryCount?: number;
  lastError?: string;
  onRetry?: () => void;
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isOnline = true,
  isRetrying = false,
  retryCount = 0,
  lastError,
  onRetry,
  className
}) => {
  const [showDetails, setShowDetails] = useState(false);

  // Auto-hide details after 5 seconds
  useEffect(() => {
    if (showDetails) {
      const timer = setTimeout(() => setShowDetails(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [showDetails]);

  const getStatusColor = () => {
    if (isRetrying) return 'warning';
    if (!isOnline) return 'error';
    return 'success';
  };

  const getStatusIcon = () => {
    if (isRetrying) return <Refresh className="animate-spin" />;
    if (!isOnline) return <WifiOff />;
    return <CheckCircle />;
  };

  const getStatusText = () => {
    if (isRetrying) return 'Reconnecting...';
    if (!isOnline) return 'Disconnected';
    return 'Connected';
  };

  const handleClick = () => {
    if (!isOnline && onRetry) {
      onRetry();
    } else {
      setShowDetails(!showDetails);
    }
  };

  return (
    <Box className={className}>
      <Chip
        icon={getStatusIcon()}
        label={getStatusText()}
        color={getStatusColor() as any}
        size="small"
        onClick={handleClick}
        sx={{
          cursor: 'pointer',
          '&:hover': {
            opacity: 0.8,
          },
        }}
      />
      
      {showDetails && (
        <Box sx={{ mt: 1 }}>
          <Alert 
            severity={isOnline ? 'success' : 'error'} 
            sx={{ maxWidth: 300 }}
          >
            <Typography variant="body2">
              {isOnline ? (
                'All systems operational'
              ) : (
                <>
                  Connection lost
                  {retryCount > 0 && (
                    <Typography variant="caption" display="block">
                      Retry attempts: {retryCount}
                    </Typography>
                  )}
                  {lastError && (
                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                      Last error: {lastError}
                    </Typography>
                  )}
                </>
              )}
            </Typography>
            
            {!isOnline && onRetry && (
              <Button
                size="small"
                startIcon={<Refresh />}
                onClick={onRetry}
                sx={{ mt: 1 }}
              >
                Retry Connection
              </Button>
            )}
          </Alert>
        </Box>
      )}
    </Box>
  );
};

export default ConnectionStatus;
