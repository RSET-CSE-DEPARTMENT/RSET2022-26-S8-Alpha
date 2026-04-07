import { createContext, useContext, useEffect, useState, useRef } from 'react';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    // Connect to WebSocket server
    ws.current = new WebSocket('ws://localhost:8000/ws');

    ws.current.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      // Try to parse as JSON to check for feedback messages
      try {
        const parsed = JSON.parse(event.data);
        
        // Handle feedback message - display only the message text
        if (parsed.type === 'feedback') {
          console.log('[FEEDBACK] Received feedback message:', parsed.message);
          setMessages(prev => [...prev, { text: parsed.message, type: 'received' }]);
          return;
        }
        
        // Handle feedback clear command - reset all messages
        if (parsed.type === 'feedback_clear') {
          console.log('[FEEDBACK] Clearing all messages');
          setMessages([]);
          return;
        }
        
        // Ignore all other JSON messages (e.g. error acks, data_updated pings)
        
      } catch (error) {
        // Not JSON — ignore silently
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    ws.current.onclose = () => {
      console.log('WebSocket Disconnected');
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const sendMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
      // Do not store outgoing frame batches in messages state
    } else {
      console.error('WebSocket is not connected');
    }
  };

  return (
    <WebSocketContext.Provider value={{ messages, sendMessage, isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
};
