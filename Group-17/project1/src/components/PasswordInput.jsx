// PasswordInput.jsx - Password input with show/hide toggle

import { useState } from 'react';
import '../css/PasswordInput.css';
import '../css/LoginInput.css';
import viewPasswordIcon from '../assets/viewpassword.svg';

function PasswordInput({ 
  id, 
  label, 
  placeholder, 
  value, 
  onChange, 
  required = false 
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="form-field">
      <label htmlFor={id} className="form-label">
        {label}
      </label>
      <div className="password-container">
        <input
          id={id}
          type={showPassword ? 'text' : 'password'}
          className="form-input password-input"
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setShowPassword(!showPassword)}
          aria-label="Toggle password visibility"
        >
          <img src={viewPasswordIcon} alt="Toggle password visibility" />
        </button>
      </div>
    </div>
  );
}

export default PasswordInput;
