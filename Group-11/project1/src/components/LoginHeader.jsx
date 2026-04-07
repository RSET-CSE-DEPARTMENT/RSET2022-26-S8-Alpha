// LoginHeader.jsx - Header component with logo and title

import '../css/LoginHeader.css';
import dumbellIcon from '../assets/dumbell.svg';

function LoginHeader() {
  return (
    <div className="login-header">
      <div className="login-logo">
        <img src={dumbellIcon} alt="Core Align Logo" />
      </div>
      <h1 className="login-title">Core Align</h1>
      <p className="login-subtitle">Welcome Back</p>
      <p className="login-description">
        Sign in to continue your fitness journey
      </p>
    </div>
  );
}

export default LoginHeader;
