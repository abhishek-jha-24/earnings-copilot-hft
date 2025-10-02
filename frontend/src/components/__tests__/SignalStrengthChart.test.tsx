import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import SignalStrengthChart from '../SignalStrengthChart';

const theme = createTheme();

const mockSubscribedTickers = ['AAPL', 'MSFT', 'GOOGL'];

const MockNotificationProvider = ({ children }: { children: React.ReactNode }) => {
  return (
    <div data-testid="notification-provider">
      {children}
    </div>
  );
};

// Mock the notification context
jest.mock('../../contexts/NotificationContext', () => ({
  useNotifications: () => ({
    notifications: [],
  }),
}));

describe('SignalStrengthChart', () => {
  it('renders without crashing', () => {
    render(
      <ThemeProvider theme={theme}>
        <MockNotificationProvider>
          <SignalStrengthChart subscribedTickers={mockSubscribedTickers} />
        </MockNotificationProvider>
      </ThemeProvider>
    );
    
    expect(screen.getByText('Real-time Signal Strength')).toBeInTheDocument();
  });

  it('displays time range selector', () => {
    render(
      <ThemeProvider theme={theme}>
        <MockNotificationProvider>
          <SignalStrengthChart subscribedTickers={mockSubscribedTickers} />
        </MockNotificationProvider>
      </ThemeProvider>
    );
    
    expect(screen.getByLabelText('Time Range')).toBeInTheDocument();
  });

  it('shows live toggle switch', () => {
    render(
      <ThemeProvider theme={theme}>
        <MockNotificationProvider>
          <SignalStrengthChart subscribedTickers={mockSubscribedTickers} />
        </MockNotificationProvider>
      </ThemeProvider>
    );
    
    expect(screen.getByLabelText('Live')).toBeInTheDocument();
  });
});
