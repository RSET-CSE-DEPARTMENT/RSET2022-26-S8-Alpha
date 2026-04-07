import { Navigate } from 'react-router-dom';
import { useFirebase } from '../context/firebase';

function ProtectedRoute({ children }) {
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

  return currentUser ? children : <Navigate to="/login" replace />;
}

export default ProtectedRoute;
