import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { NotificationEvent, DocEvent, SignalEvent, ComplianceEvent } from '../types';
import { useAuth } from './AuthContext';
import { apiService } from '../services/api';

interface NotificationContextType {
  notifications: NotificationEvent[];
  isConnected: boolean;
  clearNotifications: () => void;
  addNotification: (notification: NotificationEvent) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<NotificationEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated && user) {
      connectToSSE();
    } else {
      disconnectFromSSE();
    }

    return () => {
      disconnectFromSSE();
    };
  }, [isAuthenticated, user]);

  const connectToSSE = () => {
    if (!user) return;

    try {
      const eventSource = apiService.createEventSource(user.id);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection established');
        setIsConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const notification: NotificationEvent = {
            event: event.type || 'message',
            data,
            timestamp: new Date().toISOString(),
          };
          addNotification(notification);
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      };

      // Handle specific event types
      eventSource.addEventListener('NEW_DOC_INGESTED', (event) => {
        const data = JSON.parse((event as MessageEvent).data) as DocEvent;
        const notification: NotificationEvent = {
          event: 'NEW_DOC_INGESTED',
          data,
          timestamp: new Date().toISOString(),
        };
        addNotification(notification);
      });

      eventSource.addEventListener('NEW_SIGNAL_READY', (event) => {
        const data = JSON.parse((event as MessageEvent).data) as SignalEvent;
        const notification: NotificationEvent = {
          event: 'NEW_SIGNAL_READY',
          data,
          timestamp: new Date().toISOString(),
        };
        addNotification(notification);
      });

      eventSource.addEventListener('COMPLIANCE_ALERT', (event) => {
        const data = JSON.parse((event as MessageEvent).data) as ComplianceEvent;
        const notification: NotificationEvent = {
          event: 'COMPLIANCE_ALERT',
          data,
          timestamp: new Date().toISOString(),
        };
        addNotification(notification);
      });

      eventSource.addEventListener('connected', (event) => {
        const data = JSON.parse((event as MessageEvent).data);
        console.log('SSE connected:', data);
        setIsConnected(true);
      });

      eventSource.addEventListener('ping', (event) => {
        // Handle keepalive pings
        console.log('SSE ping received');
      });

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        setIsConnected(false);
        
        // Attempt to reconnect after a delay
        setTimeout(() => {
          if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
            connectToSSE();
          }
        }, 5000);
      };

    } catch (error) {
      console.error('Failed to establish SSE connection:', error);
      setIsConnected(false);
    }
  };

  const disconnectFromSSE = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  };

  const addNotification = (notification: NotificationEvent) => {
    setNotifications(prev => [notification, ...prev.slice(0, 49)]); // Keep last 50
  };

  const clearNotifications = () => {
    setNotifications([]);
  };

  const value: NotificationContextType = {
    notifications,
    isConnected,
    clearNotifications,
    addNotification,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};
