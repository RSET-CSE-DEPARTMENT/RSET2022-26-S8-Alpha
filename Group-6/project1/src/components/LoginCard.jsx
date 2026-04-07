// LoginCard.jsx - Card container component

import '../css/LoginCard.css';

function LoginCard({ children }) {
  return (
    <div className="login-container">
      <div className="login-card">
        {children}
      </div>
    </div>
  );
}

export default LoginCard;
