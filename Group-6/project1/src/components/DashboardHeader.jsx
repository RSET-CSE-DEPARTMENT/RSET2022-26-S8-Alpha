// DashboardHeader.jsx - Header with user greeting and logout button

import { useNavigate } from 'react-router-dom';
import { useFirebase } from '../context/firebase';
import '../css/DashboardHeader.css';
import logout from '../assets/logout.svg';

function DashboardHeader({ username }) {
  const firebase = useFirebase();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await firebase.signout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <div className="dashboard-header">
      <div className="header-user">
        <div className="user-avatar">
          {username.substring(0, 2).toUpperCase()}
        </div>
        <div className="user-info">
          <h2>Welcome back, {username}!</h2>
          <p>Ready to crush your fitness goals?</p>
        </div>
      </div>
      <button className="logout-button" onClick={handleLogout}>
        <span>
            <img src={logout} alt="logout" />
        </span> Logout
      </button>
    </div>
  );
}

export default DashboardHeader;
