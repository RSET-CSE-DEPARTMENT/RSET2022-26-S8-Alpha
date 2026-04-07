// SigninLink.jsx - Sign in link component

import '../css/SigninLink.css';

function SigninLink({ onSigninClick }) {
  return (
    <p className="signin-text">
      Already have an account?{' '}
      <a
        href="#signin"
        className="signin-link"
        onClick={(e) => {
          e.preventDefault();
          onSigninClick();
        }}
      >
        Sign in
      </a>
    </p>
  );
}

export default SigninLink;
