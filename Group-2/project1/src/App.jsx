import './App.css'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useFirebase } from './context/firebase'
import { WebSocketProvider } from './context/WebSocketContext'

import CoreAlignLogin from './pages/CoreAlignLogin';
import UserDashboard from './pages/UserDashboard';
import SignupPage from './pages/SignupPage';
import Workout from './pages/Workout';
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  const { currentUser, loading } = useFirebase();

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading...
      </div>
    );
  }

  return (
    <WebSocketProvider>
      <div className="App">
        <Routes>
          {/* Default route */}
          <Route path="/" element={<Navigate to={currentUser ? "/dashboard" : "/login"} replace />} />
        
        {/* Public routes - redirect to dashboard if already logged in */}
        <Route 
          path="/login" 
          element={currentUser ? <Navigate to="/dashboard" replace /> : <CoreAlignLogin />} 
        />
        <Route 
          path="/signup" 
          element={currentUser ? <Navigate to="/dashboard" replace /> : <SignupPage />} 
        />
        
        {/* Protected routes */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <UserDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/workout" 
          element={
            
              <Workout />
            
          } 
        />
        
        {/* Catch all */}
        <Route path="*" element={<Navigate to={currentUser ? "/dashboard" : "/login"} replace />} />
      </Routes>
      </div>
    </WebSocketProvider>
  )
  
}

export default App
