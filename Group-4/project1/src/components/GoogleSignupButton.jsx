// GoogleSignupButton.jsx - Google signup button component

import '../css/GoogleSignupButton.css';

function GoogleSignupButton({ onClick }) {
  return (
    <button 
      type="button" 
      className="google-signup-button"
      onClick={onClick}
    >
      <span className="google-icon">G</span>
      Google
    </button>
  );
}

export default GoogleSignupButton;
