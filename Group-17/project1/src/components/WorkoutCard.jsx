// WorkoutCard.jsx - Ready to Train card component

import '../css/WorkoutCard.css';
import readyToTrainIcon from '../assets/readytotrain.svg';

function WorkoutCard({ onStartWorkout }) {
  return (
    <div className="workout-card">
      <div className="workout-icon">
        <img src={readyToTrainIcon} alt="Ready to Train" />
      </div>
      <h3>Ready to Train?</h3>
      <p>Start your workout session now</p>
      <button className="start-workout-btn" onClick={onStartWorkout}>
        Start Workout
      </button>
    </div>
  );
}

export default WorkoutCard;
