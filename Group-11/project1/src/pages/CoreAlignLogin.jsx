// CoreAlignLogin.jsx - Main login page using modular components
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import LoginCard from '../components/LoginCard';
import LoginHeader from '../components/LoginHeader';
import LoginInput from '../components/LoginInput';
import PasswordInput from '../components/PasswordInput';
import LoginButton from '../components/LoginButton';
import SignupLink from '../components/SignupLink';
import { useFirebase } from '../context/firebase';

function CoreAlignLogin() {
  const firebase = useFirebase();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await firebase.signin(email, password);
      navigate('/dashboard');
    } catch (error) {
      setLoading(false);
      
      // Handle specific Firebase errors
      if (error.code === 'auth/invalid-email') {
        setError('Invalid email address.');
      } else if (error.code === 'auth/user-not-found' || error.code === 'auth/wrong-password' || error.code === 'auth/invalid-credential') {
        setError('Invalid email or password.');
      } else {
        setError('Failed to sign in. Please try again.');
      }
    }
  };

  const handleSignup = () => {
    navigate('/signup');
  };

  return (
    <LoginCard>
      <LoginHeader />
      
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
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <LoginButton type="submit" disabled={loading}>
          {loading ? 'Signing In...' : 'Sign In'}
        </LoginButton>
      </form>

      <SignupLink onSignupClick={handleSignup} />
    </LoginCard>
  );
}

export default CoreAlignLogin;
