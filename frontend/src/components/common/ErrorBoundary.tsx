import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Alert, Box, Button, Typography, Chip } from '@mui/material';
import { Refresh, WifiOff, BugReport } from '@mui/icons-material';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorType: 'network' | 'component' | 'unknown';
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'unknown',
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Determine error type based on error characteristics
    let errorType: 'network' | 'component' | 'unknown' = 'unknown';
    
    if (error.message.includes('fetch') || 
        error.message.includes('network') || 
        error.message.includes('connection') ||
        error.message.includes('timeout')) {
      errorType = 'network';
    } else if (error.stack && error.stack.includes('React')) {
      errorType = 'component';
    }

    return {
      hasError: true,
      error,
      errorInfo: null,
      errorType,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'unknown',
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { errorType } = this.state;
      
      return (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          minHeight="400px"
          p={3}
        >
          <Alert severity="error" sx={{ mb: 2, maxWidth: 600 }}>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              {errorType === 'network' ? <WifiOff /> : <BugReport />}
              <Typography variant="h6">
                {errorType === 'network' ? 'Connection Problem' : 'Something went wrong'}
              </Typography>
            </Box>
            
            <Chip 
              label={errorType === 'network' ? 'Network Error' : 'Component Error'} 
              size="small" 
              color={errorType === 'network' ? 'warning' : 'error'}
              sx={{ mb: 1 }}
            />
            
            <Typography variant="body2" color="text.secondary">
              {errorType === 'network' 
                ? 'Unable to connect to the server. Please check your internet connection.'
                : this.state.error?.message || 'An unexpected error occurred'
              }
            </Typography>
          </Alert>
          
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={this.handleRetry}
            sx={{ mt: 2 }}
          >
            {errorType === 'network' ? 'Retry Connection' : 'Try Again'}
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
