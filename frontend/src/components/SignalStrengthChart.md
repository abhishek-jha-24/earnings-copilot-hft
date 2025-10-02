# Signal Strength Chart Component

## Overview

The `SignalStrengthChart` component provides a real-time visualization of trading signal strength across multiple tickers. It displays signal strength as a line chart with interactive features for traders to monitor market signals.

## Features

### Real-time Updates
- Auto-updates every 5 seconds when live mode is enabled
- Listens to SSE notifications for new signals
- Fetches latest signal data for subscribed tickers

### Interactive Chart
- **X-axis**: Time (UTC) with configurable ranges
- **Y-axis**: Signal strength (-100 to +100)
  - Positive values: BUY signals (green)
  - Negative values: SELL signals (red)
  - Magnitude represents confidence level

### Time Range Controls
- 1 Hour
- 24 Hours  
- 7 Days
- All Time

### Interactive Features
- **Clickable markers**: Click on data points to view detailed signal information
- **Live toggle**: Pause/resume real-time updates
- **Zoom/Pan**: Built-in chart controls for detailed analysis
- **Refresh button**: Manual data refresh

### Signal Details Dialog
When clicking on a data point, shows:
- Signal action (BUY/SELL/HOLD)
- Confidence percentage
- Signal strength value
- Complete rationale
- Source citations with confidence scores

## Usage

```tsx
import SignalStrengthChart from './SignalStrengthChart';

<SignalStrengthChart 
  subscribedTickers={['AAPL', 'MSFT', 'GOOGL']}
  className="signal-strength-chart"
/>
```

## Props

| Prop | Type | Description |
|------|------|-------------|
| `subscribedTickers` | `string[]` | Array of ticker symbols to display |
| `className` | `string?` | Optional CSS class name |

## Data Structure

The component expects signal data in the following format:

```typescript
interface SignalDataPoint {
  timestamp: string;
  ticker: string;
  signalStrength: number; // -100 to +100
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number; // 0-1
  reasons: string[];
  citations: Array<{
    source: string;
    page: number;
    table: string;
    confidence: number;
  }>;
  generated_at: string;
}
```

## Styling

The component uses Material-UI theming and includes:
- Responsive design for different screen sizes
- Color-coded lines for different tickers
- Professional chart styling with grid lines
- Interactive tooltips and legends

## Dependencies

- `recharts` - Chart rendering
- `@mui/material` - UI components
- `date-fns` - Date formatting
- `react` - Core functionality

## Integration

The component integrates with:
- `useNotificationContext` - For real-time updates
- `useSubscriptions` - For ticker management
- API service - For data fetching
