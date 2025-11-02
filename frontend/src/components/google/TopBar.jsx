import { useState } from 'react';

const TopBar = ({ user, onLogout, currentDate, onNavigate, onToday, viewType, onViewChange }) => {
  const [showViewMenu, setShowViewMenu] = useState(false);

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  return (
    <div className="top-bar">
      <div className="top-bar-left">
        <button className="menu-button">
          <svg width="24" height="24" viewBox="0 0 24 24">
            <path fill="currentColor" d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>

        <div className="calendar-logo">
          <img src="https://www.gstatic.com/images/branding/product/1x/calendar_2020q4_48dp.png" alt="Calendar" />
          <span>Calendar</span>
        </div>
      </div>

      <div className="top-bar-center">
        <button className="today-button" onClick={onToday}>
          Today
        </button>

        <div className="nav-arrows">
          <button className="nav-arrow" onClick={() => onNavigate('prev')}>
            ‹
          </button>
          <button className="nav-arrow" onClick={() => onNavigate('next')}>
            ›
          </button>
        </div>

        <div className="current-month">
          {formatDate(currentDate)}
        </div>
      </div>

      <div className="top-bar-right">
        <button className="icon-button" title="Search">
          <svg width="24" height="24" viewBox="0 0 24 24">
            <path fill="currentColor" d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
          </svg>
        </button>

        <button className="icon-button" title="Help">
          <svg width="24" height="24" viewBox="0 0 24 24">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
          </svg>
        </button>

        <button className="icon-button" title="Settings">
          <svg width="24" height="24" viewBox="0 0 24 24">
            <path fill="currentColor" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.70-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.70 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
          </svg>
        </button>

        <div className="view-selector" style={{position: 'relative'}}>
          <button onClick={() => setShowViewMenu(!showViewMenu)} style={{all: 'inherit', cursor: 'pointer'}}>
            {viewType === 'week' ? '4 days' : viewType === 'month' ? 'Month' : 'Day'}
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="currentColor" d="M7 10l5 5 5-5z"/>
            </svg>
          </button>

          {showViewMenu && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              background: 'var(--gc-bg-secondary)',
              border: '1px solid var(--gc-border)',
              borderRadius: 'var(--border-radius-md)',
              marginTop: '4px',
              minWidth: '120px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
              zIndex: 1000
            }}>
              {['Day', 'Week', 'Month'].map(type => (
                <button
                  key={type}
                  onClick={() => {
                    onViewChange(type.toLowerCase());
                    setShowViewMenu(false);
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 16px',
                    textAlign: 'left',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--gc-text-primary)',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => e.target.style.background = 'var(--gc-bg-hover)'}
                  onMouseLeave={(e) => e.target.style.background = 'transparent'}
                >
                  {type}
                </button>
              ))}
            </div>
          )}
        </div>

        <button className="profile-button" title={user.name} onClick={onLogout}>
          {user.name.charAt(0).toUpperCase()}
        </button>
      </div>
    </div>
  );
};

export default TopBar;
