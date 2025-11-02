/**
 * Main App Component - Google Calendar Clone for RL Training
 *
 * This app mimics Google Calendar's UI/UX exactly for RL model training.
 * The model will interact with the app through screenshots to learn calendar tasks.
 */

import { useState, useEffect } from 'react';
import './styles/GoogleCalendar.css';
import CalendarMain from './components/google/CalendarMain';
import Sidebar from './components/google/Sidebar';
import TopBar from './components/google/TopBar';
import EventModal from './components/google/EventModal';
import { getUsers } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [showUserSelect, setShowUserSelect] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await getUsers();
      setUsers(data);

      // Check if user is in sessionStorage
      const savedUser = sessionStorage.getItem('calendar_user');
      if (savedUser) {
        const parsedUser = JSON.parse(savedUser);
        setUser(parsedUser);
        setShowUserSelect(false);
      }
    } catch (err) {
      console.error('Error loading users:', err);
    }
  };

  const handleUserSelect = (selectedUser) => {
    setUser(selectedUser);
    sessionStorage.setItem('calendar_user', JSON.stringify(selectedUser));
    setShowUserSelect(false);
  };

  const handleLogout = () => {
    setUser(null);
    sessionStorage.removeItem('calendar_user');
    setShowUserSelect(true);
  };

  // User selection screen
  if (showUserSelect) {
    return (
      <div className="user-select-screen">
        <div className="user-select-card">
          <img
            src="https://www.gstatic.com/images/branding/product/1x/calendar_2020q4_48dp.png"
            alt="Google Calendar"
            className="calendar-logo-large"
          />
          <h1>Google Calendar Gym</h1>
          <p>Select a user to continue</p>

          <div className="user-list">
            {users.map((u) => (
              <button
                key={u.id}
                className="user-select-button"
                onClick={() => handleUserSelect(u)}
              >
                <div className="user-avatar">{u.name.charAt(0).toUpperCase()}</div>
                <div className="user-info">
                  <div className="user-name">{u.name}</div>
                  <div className="user-email">{u.email}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Main Google Calendar UI
  return (
    <div className="google-calendar">
      <TopBar user={user} onLogout={handleLogout} />
      <div className="calendar-container">
        <Sidebar user={user} />
        <CalendarMain user={user} />
      </div>
    </div>
  );
}

export default App;
