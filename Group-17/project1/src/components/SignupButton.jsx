// SignupButton.jsx - Create account button component

import '../css/SignupButton.css';

function SignupButton({ children, onClick, type = 'submit' }) {
  return (
    <button 
      type={type} 
      className="signup-button"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export default SignupButton;
