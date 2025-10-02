# 📈 Earnings Copilot HFT - Frontend

Modern TypeScript React frontend for the Earnings Copilot HFT system.

## Features

- 🎨 **Modern UI**: Material-UI with dark theme
- 📊 **Real-time Dashboard**: Live trading signals and KPI displays
- 🔔 **Live Notifications**: Server-Sent Events for instant updates
- 📄 **Document Management**: Admin panel for PDF uploads
- 🔍 **Search Interface**: Semantic search across documents
- 📈 **Data Visualization**: Charts and metrics display
- 🔐 **Authentication**: Role-based access (Admin/Trader)

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

## Architecture

```
src/
├── components/          # React components
│   ├── AdminPanel.tsx      # Document upload interface
│   ├── TraderDashboard.tsx # Trading signals & KPIs
│   ├── SubscriptionManager.tsx # Notification subscriptions
│   ├── NotificationPanel.tsx   # Live SSE notifications
│   └── LoginForm.tsx       # Authentication form
├── contexts/           # React contexts
│   ├── AuthContext.tsx     # Authentication state
│   └── NotificationContext.tsx # SSE notifications
├── services/           # API services
│   └── api.ts             # HTTP client & API calls
├── types/              # TypeScript definitions
│   └── index.ts           # All type definitions
└── hooks/              # Custom React hooks
```

## Key Components

### TraderDashboard
- **Signal Display**: BUY/SELL/HOLD with confidence scores
- **KPI Cards**: Revenue, EPS, margins with YoY changes
- **Search Interface**: Document search with citations
- **Export**: PDF memo generation

### AdminPanel
- **Document Upload**: PDF processing with metadata
- **System Stats**: Processing metrics and health
- **Document Types**: Earnings, compliance, filings

### NotificationPanel
- **Real-time Updates**: SSE connection status
- **Event Types**: Document ingestion, signals, compliance alerts
- **Visual Indicators**: Color-coded notifications

## API Integration

The frontend communicates with the FastAPI backend through:

- **REST API**: Standard CRUD operations
- **Server-Sent Events**: Real-time notifications
- **File Upload**: Multipart form data for PDFs
- **Authentication**: X-API-Key header

## Environment Setup

The app expects the API server at `http://localhost:8000`. This is configured via:

1. **Proxy**: `package.json` proxy setting
2. **API Service**: Base URL in `services/api.ts`

## Demo Usage

1. **Login**: Use demo credentials
   - Admin: `admin-secret`
   - Trader: `trader-secret`

2. **Admin Flow**:
   - Upload PDF documents
   - Monitor processing stats
   - View system health

3. **Trader Flow**:
   - Subscribe to tickers
   - View trading signals
   - Export investment memos
   - Monitor real-time notifications

## Real-time Features

### Server-Sent Events
- Automatic reconnection
- Connection status display
- Event filtering by subscription

### Notification Types
- `NEW_DOC_INGESTED`: Document processed
- `NEW_SIGNAL_READY`: Trading signal generated
- `COMPLIANCE_ALERT`: Margin requirement changes

## Development

### Adding New Components
1. Create component in `src/components/`
2. Add to main `App.tsx`
3. Update types in `src/types/`

### API Integration
1. Add endpoint to `src/services/api.ts`
2. Define types in `src/types/`
3. Use in components with error handling

### Styling
- Material-UI theme in `App.tsx`
- Dark mode enabled
- Responsive design with Grid system

## Production Build

```bash
# Build optimized bundle
npm run build

# Serve static files
npx serve -s build
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Built with React 19, TypeScript 4.9, and Material-UI 7.