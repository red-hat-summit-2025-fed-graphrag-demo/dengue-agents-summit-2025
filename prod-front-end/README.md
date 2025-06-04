# WebSocket Chat Frontend for Dengue API Testing

This is a Next.js chat application for testing the WebSocket API running at localhost:8000.

## Features

- Real-time chat interface with WebSocket connectivity
- Auto-reconnect functionality
- Message history display
- Connection status indicators
- Clear chat functionality

## Getting Started

### Prerequisites

- Make sure your WebSocket API is running on `localhost:8000`
- Node.js and npm installed

### Running the Application

1. First, start your WebSocket API server on port 8000:
   ```bash
   # Navigate to the API directory and run your WebSocket server
   cd ../api
   ./start_websocket.sh
   ```

2. In a separate terminal, start the Next.js development server:
   ```bash
   # You can use the provided script
   ./start-frontend.sh
   
   # Or run it directly
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) with your browser to see the chat interface.

## Usage

- The chat interface will automatically attempt to connect to `ws://localhost:8000/ws`
- Type your messages in the input field and press Enter or click the send button
- Connection status is shown below the input field
- You can clear the chat history or manually reconnect using the buttons at the top

## Development

The main components are:

- `src/hooks/useWebSocket.ts` - WebSocket connection management hook
- `src/components/ChatInterface.tsx` - Main chat UI component
- `src/components/MessageItem.tsx` - Individual message display
- `src/components/MessageInput.tsx` - Message input field

## Troubleshooting

- If you see connection errors, ensure your WebSocket API is running correctly on port 8000
- Check browser console for any WebSocket-related errors
- If messages aren't sending, verify the WebSocket server is configured to accept the message format you're sending
