import React from 'react';
import LoginForm from '../components/LoginForm';

const LoginPage: React.FC = () => {
  return (
    <div className="login-page">
      <div className="login-container">
        <h1>Video to MP3 Converter</h1>
        <LoginForm />
      </div>
    </div>
  );
};

export default LoginPage;