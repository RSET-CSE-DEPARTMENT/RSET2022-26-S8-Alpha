// LoginInput.jsx - Reusable input component with label

import '../css/LoginInput.css';

function LoginInput({ 
  id, 
  label, 
  type = 'text', 
  placeholder, 
  value, 
  onChange, 
  required = false 
}) {
  return (
    <div className="form-field">
      <label htmlFor={id} className="form-label">
        {label}
      </label>
      <input
        id={id}
        type={type}
        className="form-input"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
      />
    </div>
  );
}

export default LoginInput;
