import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary — catches render errors and shows
 * a graceful fallback instead of a white screen.
 *
 * Usage:
 *   <ErrorBoundary fallbackTitle="Błąd sekcji">
 *     <SomeComponent />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            m: 2,
            textAlign: 'center',
            border: '1px solid',
            borderColor: 'error.light',
            borderRadius: 2,
            bgcolor: 'error.50',
          }}
        >
          <ErrorOutlineIcon sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom color="error.main">
            {this.props.fallbackTitle || 'Coś poszło nie tak'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {this.state.error?.message || 'Wystąpił nieoczekiwany błąd.'}
          </Typography>
          <Button
            variant="outlined"
            color="error"
            onClick={this.handleRetry}
            size="small"
          >
            Spróbuj ponownie
          </Button>
        </Paper>
      );
    }

    return this.props.children;
  }
}
