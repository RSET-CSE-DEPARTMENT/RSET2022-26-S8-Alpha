import { useEffect, useRef } from 'react'
import { useWebSocket } from '../context/WebSocketContext'
import '../css/DataSender.css'

function DataSender() {
  const { messages, isConnected } = useWebSocket()
  const messagesEndRef = useRef(null)

  // Auto-scroll to the last message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="data-sender-container">
      <div className="header">
        <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
      </div>

      <div className="messages-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message-item ${msg.type}`}>
            <span className="message-type">{msg.type === 'sent' ? '→' : '←'}</span>
            <span className="message-text">{msg.text}</span>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

export default DataSender
