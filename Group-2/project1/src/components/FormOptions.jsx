// FormOptions.jsx - Remember me checkbox and forgot password link

import '../css/FormOptions.css';

function FormOptions({ rememberMe, onRememberMeChange, onForgotPassword }) {
  return (
    <div className="form-options">
      <label className="remember-label">
        <input
          type="checkbox"
          className="remember-checkbox"
          checked={rememberMe}
          onChange={(e) => onRememberMeChange(e.target.checked)}
        />
        Remember me
      </label>
      <a
        href="#forgot"
        className="forgot-link"
        onClick={(e) => {
          e.preventDefault();
          onForgotPassword();
        }}
      >
        Forgot password?
      </a>
    </div>
  );
}

export default FormOptions;
