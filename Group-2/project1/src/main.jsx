import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import {BrowserRouter} from 'react-router-dom'
import { FirebaseProvider } from './context/firebase.jsx'
import Workout from './pages/Workout.jsx'
import { WebSocketProvider } from './context/WebSocketContext.jsx'
import DataSender from './components/DataSender.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <FirebaseProvider>
        <App />
      </FirebaseProvider>
    </BrowserRouter> 
  </StrictMode>,
)
