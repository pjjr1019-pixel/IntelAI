'use client';

import { useEffect, useRef, useState } from 'react';

export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const pingInterval = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  useEffect(() => {
    const connect = () => {
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        console.warn(`WebSocket: Max reconnection attempts (${maxReconnectAttempts}) reached. Giving up.`);
        return;
      }

      console.log(`WebSocket: Attempting to connect to ${url}`);
      try {
        ws.current = new WebSocket(url);
        reconnectAttempts.current += 1;
      } catch (error) {
        console.warn('WebSocket: Failed to create connection:', error);
        setIsConnected(false);
        return;
      }

      ws.current.onopen = () => {
        console.log('WebSocket: Connection opened successfully');
        setIsConnected(true);
        reconnectAttempts.current = 0; // Reset on successful connection
        // Send ping every 30 seconds to keep connection alive
        pingInterval.current = setInterval(() => {
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ command: 'ping' }));
          }
        }, 30000);
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setMessages(prev => [...prev, data]);
      };

      ws.current.onclose = (event) => {
        console.log(`WebSocket: Connection closed (code: ${event.code}, reason: ${event.reason})`);
        setIsConnected(false);
        if (pingInterval.current) {
          clearInterval(pingInterval.current);
          pingInterval.current = null;
        }

        // Only reconnect if we haven't exceeded max attempts and it's not a normal closure
        if (reconnectAttempts.current < maxReconnectAttempts && event.code !== 1000) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000); // Exponential backoff, max 30s
          console.warn(`WebSocket: Connection closed (code: ${event.code}). Reconnecting in ${delay}ms...`);
          reconnectTimeout.current = setTimeout(connect, delay);
        } else if (event.code !== 1000) {
          console.warn(`WebSocket: Connection closed (code: ${event.code}). Not reconnecting.`);
        }
      };

      ws.current.onerror = (error) => {
        // Use warning instead of error since reconnection logic handles failures
        console.warn('WebSocket: Connection error:', error, 'URL:', url, 'ReadyState:', ws.current?.readyState);
        setIsConnected(false);
      };
    };

    connect();

    return () => {
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url]);

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  return { isConnected, messages, sendMessage };
}