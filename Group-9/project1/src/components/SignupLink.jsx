// SignupLink.jsx - Sign up link component

import '../css/SignupLink.css';

function SignupLink({ onSignupClick }) {
  return (
    <p className="signup-text">
      Don't have an account?{' '}
      <a
        href="#signup"
        className="signup-link"
        onClick={(e) => {
          e.preventDefault();
          onSignupClick();
        }}
      >
        Sign up for free
      </a>
    </p>
  );
}

export default SignupLink;
