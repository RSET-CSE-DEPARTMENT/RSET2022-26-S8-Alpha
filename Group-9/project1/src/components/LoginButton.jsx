// LoginButton.jsx - Sign in button component

import '../css/LoginButton.css';

function LoginButton({ children, onClick, type = 'submit' }) {
  return (
    <button 
      type={type} 
      className="signin-button"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export default LoginButton;
