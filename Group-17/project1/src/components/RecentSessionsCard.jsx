// RecentSessionsCard.jsx - Recent workout sessions list

import '../css/RecentSessionsCard.css';
import recentSessionsIcon from '../assets/recentsessions.svg';
import sessionDumbellIcon from '../assets/recentsessiondumbell.svg';

function RecentSessionsCard({ sessions, onViewDetails, showViewAll, isViewingAll, onToggleViewAll }) {
  return (
    <div className="recent-sessions-card">
      <div className="card-header">
        <span className="card-icon">
          <img src={recentSessionsIcon} alt="Recent Sessions" />
        </span>
        <h3 className="card-title">Recent Sessions</h3>
        {showViewAll && (
          <button 
            className="view-all-btn"
            onClick={onToggleViewAll}
          >
            {isViewingAll ? 'Show Less' : 'View All'}
          </button>
        )}
      </div>
      
      
      <div className={`sessions-list ${isViewingAll ? 'expanded' : ''}`}>
        {sessions.map((session, index) => (
          <div key={index} className="session-item">
            <div className="session-left">
              <div className="session-icon">
                <img src={sessionDumbellIcon} alt={session.name} />
              </div>
              <div className="session-info">
                <h4>{session.name}</h4>
                <p>{session.date}</p>
              </div>
            </div>
            
            <div className="session-right">
              <div className="session-duration">
                <span className="duration-value">{session.duration}</span>
                <span className="duration-label">Duration</span>
              </div>
              <button 
                className="view-details-btn"
                onClick={() => onViewDetails(session)}
              >
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RecentSessionsCard;
