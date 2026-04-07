// WeeklyGoalCard.jsx - Weekly goal progress component

import '../css/WeeklyGoalCard.css';
import weeklyGoalIcon from '../assets/weeklygoal.svg';

function WeeklyGoalCard({ current, target }) {
  const percentage = (current / target) * 100;
  const remaining = target - current;

  return (
    <div className="weekly-goal-card">
      <div className="card-header">
        <span className="card-icon">
          <img src={weeklyGoalIcon} alt="Weekly Goal" />
        </span>
        <h3 className="card-title">Weekly Goal</h3>
      </div>
      
      <div className="goal-progress">
        <div className="progress-label">
          <span>Progress</span>
          <span className="progress-count">{current}/{target} workouts</span>
        </div>
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
      </div>
      
      <p className="goal-message">
        {remaining > 0 
          ? `${remaining} more workout${remaining > 1 ? 's' : ''} to reach your goal!`
          : '🎉 Goal achieved! Keep it up!'}
      </p>
    </div>
  );
}

export default WeeklyGoalCard;
