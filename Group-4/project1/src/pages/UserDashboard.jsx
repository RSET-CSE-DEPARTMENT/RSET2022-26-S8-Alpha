// UserDashboard.jsx - Main dashboard page

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardHeader from '../components/DashboardHeader';
import WorkoutCard from '../components/WorkoutCard';
import WeeklyGoalCard from '../components/WeeklyGoalCard';
import QuickStatsCard from '../components/QuickStatsCard';
import { useFirebase } from '../context/firebase';
import RecentSessionsCard from '../components/RecentSessionsCard';
import '../css/DashboardContainer.css';
import '../css/StatsGrid.css';
import '../css/ErrorStates.css';

function UserDashboard() {
  const navigate = useNavigate();
  const firebase = useFirebase();
  
  const [userData, setUserData] = useState(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recentSessions, setRecentSessions] = useState([]);
  const [allSessions, setAllSessions] = useState([]);
  const [showAllSessions, setShowAllSessions] = useState(false);

  // Fetch user data from Firestore
  useEffect(() => {
    const fetchUserData = async () => {
      if (!firebase.currentUser) {
        setDataLoading(false);
        return;
      }

      try {
        setDataLoading(true);
        const data = await firebase.getUserData(firebase.currentUser.uid);
        setUserData(data);
        
        // Fetch recent sessions (limited to 4)
        const sessions = await firebase.getRecentSessions(firebase.currentUser.uid, 4);
        setRecentSessions(sessions);
        
        // Fetch all sessions to check if there are more than 4
        const allSessionsData = await firebase.getRecentSessions(firebase.currentUser.uid);
        setAllSessions(allSessionsData);
        
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error("Error fetching user data:", err);
      } finally {
        setDataLoading(false);
      }
    };

    fetchUserData();
  }, [firebase.currentUser]);

  // Handle logout when error occurs
  const handleErrorLogout = async () => {
    try {
      await firebase.signout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const handleStartWorkout = () => {
    navigate('/workout');
  };

  const handleViewDetails = (session) => {
    alert(`Viewing details for ${session.type} session`);
    // Add your view details logic here
  };

  // Show loading state
  if (dataLoading) {
    return (
      <div className="loading-state-container">
        Loading dashboard...
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="error-state-container">
        <div className="error-message">
          Error: {error}
        </div>
        <button onClick={handleErrorLogout} className="error-logout-button">
          Logout
        </button>
      </div>
    );
  }

  // Show error if no user data
  if (!userData) {
    return (
      <div className="error-state-container">
        <div className="no-data-message">
          No user data found
        </div>
        <button onClick={handleErrorLogout} className="error-logout-button">
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        {/* Header */}
        <DashboardHeader 
          username={userData.name}
        />

        {/* Top Cards Row - Workout, Weekly Goal, Quick Stats */}
        <div className="top-cards-row">
          <WorkoutCard onStartWorkout={handleStartWorkout} />
          <WeeklyGoalCard 
            current={0}
            target={userData.weeklyWorkoutsTarget} 
          />
          <QuickStatsCard 
            dayStreak={userData.dayStreak}
            totalWorkouts={userData.totalWorkouts}
            avgDuration={userData.avgDurationMinutes}
          />
        </div>

        {/* Recent Sessions */}
        <RecentSessionsCard 
          sessions={showAllSessions ? allSessions : recentSessions}
          onViewDetails={handleViewDetails}
          showViewAll={allSessions.length > 4}
          isViewingAll={showAllSessions}
          onToggleViewAll={() => setShowAllSessions(!showAllSessions)}
        />
      </div>
    </div>
  );
}

export default UserDashboard;
