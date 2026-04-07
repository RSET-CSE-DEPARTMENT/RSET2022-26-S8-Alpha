// SignupHeader.jsx - Header component for signup page

import '../css/SignupHeader.css';
import dumbellIcon from '../assets/dumbell.svg';

function SignupHeader() {
  return (
    <div className="signup-header">
      <div className="signup-logo">
        <img src={dumbellIcon} alt="FitTrack Pro Logo" />
      </div>
      <h1 className="signup-title">Core Align</h1>
      <h2 className="signup-main-title">Create Your Account</h2>
      <p className="signup-description">
        Start your fitness journey today
      </p>
    </div>
  );
}

export default SignupHeader;
