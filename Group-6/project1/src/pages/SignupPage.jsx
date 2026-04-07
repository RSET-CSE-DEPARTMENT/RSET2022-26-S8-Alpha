// SignupPage.jsx - Main signup page using modular components
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFirebase } from '../context/firebase';
import LoginCard from '../components/LoginCard';
import SignupHeader from '../components/SignupHeader';
import LoginInput from '../components/LoginInput';
import PasswordInput from '../components/PasswordInput';
import SignupButton from '../components/SignupButton';
import SigninLink from '../components/SigninLink';
import '../css/SignupPage.css';

function SignupPage() {
  const firebase = useFirebase();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Password validation
    if (password !== confirmPassword) {
      setError('Passwords do not match!');
      return;
    }
    
    setLoading(true);
    
    try {
      await firebase.signup(email, password, fullName);
      navigate('/dashboard');
    } catch (error) {
      setLoading(false);
      
      // Handle specific Firebase errors
      if (error.code === 'auth/email-already-in-use') {
        setError('An account with this email already exists.');
      } else if (error.code === 'auth/invalid-email') {
        setError('Invalid email address.');
      } else {
        setError('Failed to create account. Please try again.');
      }
    }
  };

  const handleSignin = () => {
    navigate('/login');
  };

  return (
    <LoginCard>
      <SignupHeader />
      
      {error && (
        <div style={{
          padding: '12px',
          marginBottom: '16px',
          backgroundColor: '#fee',
          color: '#c33',
          borderRadius: '8px',
          fontSize: '14px'
        }}>
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <LoginInput
          id="fullName"
          label="Full Name"
          type="text"
          placeholder="Enter your full name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          required
        />

        <LoginInput
          id="email"
          label="Email"
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <PasswordInput
          id="password"
          label="Password"
          placeholder="Create a password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <PasswordInput
          id="confirmPassword"
          label="Confirm Password"
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <SignupButton type="submit" disabled={loading}>
          {loading ? 'Creating Account...' : 'Create Account'}
        </SignupButton>
      </form>

      <SigninLink onSigninClick={handleSignin} />
    </LoginCard>
  );
}

export default SignupPage;
