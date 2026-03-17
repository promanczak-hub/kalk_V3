import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { Snackbar, Alert, type AlertColor } from '@mui/material';

interface Notification {
  id: number;
  message: string;
  severity: AlertColor;
}

interface NotificationContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

let _notifyId = 0;

/**
 * Global notification (toast) provider.
 *
 * Wrap your app:
 *   <NotificationProvider><App /></NotificationProvider>
 *
 * Use in any component:
 *   const notify = useNotification();
 *   notify.success("Zapisano!");
 */
export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback((message: string, severity: AlertColor) => {
    const id = ++_notifyId;
    setNotifications((prev) => [...prev, { id, message, severity }]);
  }, []);

  const removeNotification = useCallback((id: number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const value: NotificationContextValue = {
    success: (msg) => addNotification(msg, 'success'),
    error: (msg) => addNotification(msg, 'error'),
    warning: (msg) => addNotification(msg, 'warning'),
    info: (msg) => addNotification(msg, 'info'),
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
      {notifications.map((n) => (
        <Snackbar
          key={n.id}
          open
          autoHideDuration={4000}
          onClose={() => removeNotification(n.id)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert
            onClose={() => removeNotification(n.id)}
            severity={n.severity}
            variant="filled"
            sx={{ width: '100%', minWidth: 300 }}
          >
            {n.message}
          </Alert>
        </Snackbar>
      ))}
    </NotificationContext.Provider>
  );
}

export function useNotification(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotification must be used inside NotificationProvider');
  }
  return ctx;
}
