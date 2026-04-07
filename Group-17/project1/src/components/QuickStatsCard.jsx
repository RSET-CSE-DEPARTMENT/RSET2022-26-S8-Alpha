// QuickStatsCard.jsx - Quick statistics display

import '../css/QuickStatsCard.css';
import quickStatsIcon from '../assets/quickstats.svg';

function QuickStatsCard({ dayStreak, totalWorkouts, avgDuration }) {
  return (
    <div className="quick-stats-card">
      <div className="card-header">
        <span className="card-icon">
          <img src={quickStatsIcon} alt="Quick Stats" />
        </span>
        <h3 className="card-title">Quick Stats</h3>
      </div>
      
      <div className="stats-content">
        <div className="stat-item">
          <span className="stat-value">{dayStreak}</span>
          <span className="stat-label">Day Streak</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{totalWorkouts}</span>
          <span className="stat-label">Total Workouts</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{avgDuration}m</span>
          <span className="stat-label">Avg Duration</span>
        </div>
      </div>
    </div>
  );
}

export default QuickStatsCard;
