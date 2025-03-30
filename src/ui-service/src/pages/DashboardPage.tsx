import React from 'react';
import { useNavigate } from 'react-router-dom';
import VideoUpload from '../components/VideoUpload';
import { useAuth } from '../services/AuthContext';

const DashboardPage: React.FC = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>Video to MP3 Converter</h1>
        <button className="logout-button" onClick={handleLogout}>
          Logout
        </button>
      </header>
      
      <main className="dashboard-content">
        <VideoUpload />
      </main>
      
      <footer className="dashboard-footer">
        <p>&copy; {new Date().getFullYear()} Video to MP3 Converter</p>
      </footer>
    </div>
  );
};

export default DashboardPage;