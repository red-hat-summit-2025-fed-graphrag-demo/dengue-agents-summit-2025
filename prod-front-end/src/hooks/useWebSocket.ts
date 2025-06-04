"use client";

import { useState, useEffect, useCallback, useRef } from 'react';

interface UseWebSocketOptions {
  onOpen?: (event: Event) => void;
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  reconnectOnClose?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export interface WebSocketMessage {
  type: string;
  content: string;
  timestamp?: string;
  sender?: 'user' | 'server';
  agent_id?: string;
  data?: any;
  message_type?: string;
  workflow_name?: string;
  message?: string;
  error?: string;
}

const useWebSocket = (url: string | null, options: UseWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [error, setError] = useState<Event | null>(null);
  const webSocketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const {
    onOpen,
    onMessage,
    onError,
    onClose,
    reconnectOnClose = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const connect = useCallback(() => {
    // Don't attempt to connect if URL is null or empty
    if (!url) {
      console.log('No WebSocket URL provided, connection skipped');
      setIsConnected(false);
      return;
    }
    
    try {
      const ws = new WebSocket(url);
      webSocketRef.current = ws;

      ws.onopen = (event) => {
        console.log('WebSocket connection opened');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        if (onOpen) onOpen(event);
      };

      ws.onmessage = (event) => {
        console.log('WebSocket message received:', event.data);
        try {
          // Try to parse the message as JSON
          const data = JSON.parse(event.data);
          console.log('Parsed message data:', data);

          // Handle different message types
          if (data.type === 'connected') {
            // Handle connection message
            setMessages((prev) => [
              ...prev,
              {
                type: 'connected',
                content: data.message || `Connected to ${data.workflow_name || 'workflow'}`,
                message: data.message,
                workflow_name: data.workflow_name,
                timestamp: data.timestamp || new Date().toISOString(),
                sender: 'server'
              }
            ]);
          } else if (data.type === 'stream_update') {
            // Handle stream updates for thinking/processing
            setMessages((prev) => [
              ...prev,
              {
                type: 'stream_update',
                content: data.content || '',
                message_type: data.message_type || '',
                agent_id: data.agent_id || 'System',
                data: data.data,
                timestamp: data.timestamp || new Date().toISOString(),
                sender: 'server'
              }
            ]);
          } else if (data.type === 'workflow_result' || data.type === 'workflow_error') {
            // Handle final result or error
            setMessages((prev) => [
              ...prev,
              {
                type: data.type,
                content: data.content || data.error || 'No response available',
                timestamp: data.timestamp || new Date().toISOString(),
                sender: 'server',
                data: data
              }
            ]);
          } else if (data.error) {
            // Handle error messages
            setMessages((prev) => [
              ...prev,
              {
                type: 'error',
                content: data.error || 'An error occurred',
                timestamp: data.timestamp || new Date().toISOString(),
                sender: 'server'
              }
            ]);
          } else {
            // Handle any other message type
            setMessages((prev) => [
              ...prev,
              {
                type: data.type || 'message',
                content: data.content || data.message || JSON.stringify(data),
                timestamp: data.timestamp || new Date().toISOString(),
                sender: 'server',
                data: data
              }
            ]);
          }
          
          if (onMessage) onMessage(event);
        } catch (error) {
          console.error('Failed to parse message:', error);
          // Handle plain text messages or other formats
          setMessages((prev) => [
            ...prev,
            { 
              type: 'text', 
              content: String(event.data), 
              timestamp: new Date().toISOString(),
              sender: 'server'
            },
          ]);
          if (onMessage) onMessage(event);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError(event);
        if (onError) onError(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket connection closed');
        setIsConnected(false);
        if (onClose) onClose(event);

        if (reconnectOnClose && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          reconnectIntervalRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  }, [url, onOpen, onMessage, onError, onClose, reconnectOnClose, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (webSocketRef.current) {
      webSocketRef.current.close();
      webSocketRef.current = null;
    }

    if (reconnectIntervalRef.current) {
      clearTimeout(reconnectIntervalRef.current);
      reconnectIntervalRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: string | object) => {
    if (!webSocketRef.current || webSocketRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return false;
    }

    try {
      const messageToSend = typeof message === 'string' ? message : JSON.stringify(message);
      console.log('Sending message:', messageToSend);
      webSocketRef.current.send(messageToSend);
      
      // Add user message to messages state
      if (typeof message === 'string') {
        setMessages((prev) => [
          ...prev,
          {
            type: 'text',
            content: message,
            timestamp: new Date().toISOString(),
            sender: 'user'
          }
        ]);
      } else if (typeof message === 'object' && message !== null) {
        // Ensure the object conforms to WebSocketMessage type
        const typedMessage = message as any;
        const content = typedMessage.message || JSON.stringify(message);
        
        setMessages((prev) => [
          ...prev,
          {
            type: 'text',
            content: content,
            timestamp: new Date().toISOString(),
            sender: 'user'
          }
        ]);
      }
      
      return true;
    } catch (error) {
      console.error('Failed to send message:', error);
      return false;
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    // Disconnect from any existing connection before connecting to a new one
    if (webSocketRef.current) {
      console.log('Disconnecting previous WebSocket connection before creating a new one');
      disconnect();
    }
    
    // Only connect if we have a URL
    if (url) {
      console.log(`Connecting to WebSocket: ${url}`);
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect, url]);

  return { isConnected, messages, error, sendMessage, clearMessages, reconnect: connect };
};

export default useWebSocket;