import { useState, useEffect } from 'react';
import Toast from './Toast';

/**
 * SimulatedPopups component generates random UI popups for testing/demo purposes
 *
 * Types of popups:
 * 1. Reminder notifications (transient toasts)
 * 2. Meeting starting notifications (transient toasts)
 * 3. Event detail modal (modal dialog)
 * 4. Permission denied modal (modal dialog)
 */
function SimulatedPopups({ enabled = false }) {
  const [toasts, setToasts] = useState([]);
  const [modal, setModal] = useState(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Schedule random popups every 20-60 seconds
    const scheduleNextPopup = () => {
      const delay = Math.random() * 40000 + 20000; // 20-60 seconds
      return setTimeout(() => {
        showRandomPopup();
        scheduleNextPopup();
      }, delay);
    };

    const timer = scheduleNextPopup();

    return () => {
      clearTimeout(timer);
    };
  }, [enabled]);

  const showRandomPopup = () => {
    const popupType = Math.random();

    // Add small timing offset for frame variation (0-2 seconds)
    const timingOffset = Math.random() * 2000;

    setTimeout(() => {
      if (popupType < 0.4) {
        // 40% - Reminder notification
        showReminderToast();
      } else if (popupType < 0.7) {
        // 30% - Meeting starting notification
        showMeetingStartingToast();
      } else if (popupType < 0.85) {
        // 15% - Event detail modal
        showEventDetailModal();
      } else {
        // 15% - Permission denied modal
        showPermissionDeniedModal();
      }
    }, timingOffset);
  };

  const showReminderToast = () => {
    const messages = [
      'Team Meeting in 15 minutes',
      'Daily Standup in 10 minutes',
      'Client Call in 30 minutes',
      'Sprint Planning in 1 hour',
      'Code Review in 5 minutes',
      '1:1 with Manager in 20 minutes',
    ];

    const message = messages[Math.floor(Math.random() * messages.length)];

    addToast({
      id: Date.now(),
      message,
      type: 'reminder',
      duration: 5000,
    });
  };

  const showMeetingStartingToast = () => {
    const messages = [
      'Team Meeting is starting now!',
      'Project Review starting soon',
      'Daily Standup is about to begin',
      'Workshop session starting in 2 minutes',
      'Demo Day presentation starting now',
    ];

    const message = messages[Math.floor(Math.random() * messages.length)];

    addToast({
      id: Date.now(),
      message,
      type: 'info',
      duration: 4000,
    });
  };

  const showEventDetailModal = () => {
    const events = [
      {
        title: 'Team Meeting',
        time: '2:00 PM - 3:00 PM',
        location: 'Conference Room A',
        attendees: 5,
      },
      {
        title: 'Client Presentation',
        time: '10:00 AM - 11:30 AM',
        location: 'Zoom',
        attendees: 8,
      },
      {
        title: 'Sprint Planning',
        time: '9:00 AM - 10:30 AM',
        location: 'Office',
        attendees: 12,
      },
    ];

    const event = events[Math.floor(Math.random() * events.length)];

    setModal({
      type: 'event-detail',
      data: event,
    });

    // Auto-close after 8-12 seconds
    setTimeout(() => {
      setModal(null);
    }, Math.random() * 4000 + 8000);
  };

  const showPermissionDeniedModal = () => {
    const reasons = [
      'You do not have permission to edit this calendar',
      'This event can only be modified by the organizer',
      'You need writer access to create events',
      'Calendar sharing permissions required',
    ];

    const reason = reasons[Math.floor(Math.random() * reasons.length)];

    setModal({
      type: 'permission-denied',
      data: { reason },
    });

    // Auto-close after 6-10 seconds
    setTimeout(() => {
      setModal(null);
    }, Math.random() * 4000 + 6000);
  };

  const addToast = (toast) => {
    setToasts((prev) => [...prev, toast]);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const closeModal = () => {
    setModal(null);
  };

  if (!enabled) {
    return null;
  }

  return (
    <>
      {/* Toast notifications - stacked */}
      <div className="fixed top-20 right-6 z-50 flex flex-col gap-3">
        {toasts.map((toast, index) => (
          <div
            key={toast.id}
            style={{
              transform: `translateY(${index * 80}px)`,
              transition: 'transform 0.3s ease',
            }}
          >
            <Toast
              message={toast.message}
              type={toast.type}
              duration={toast.duration}
              onClose={() => removeToast(toast.id)}
            />
          </div>
        ))}
      </div>

      {/* Modal dialogs */}
      {modal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 animate-fade-in"
          onClick={closeModal}
          data-automation-id="simulated-modal-overlay"
        >
          <div
            className="bg-white rounded-lg shadow-2xl max-w-md w-full mx-4 animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {modal.type === 'event-detail' && (
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900">
                    {modal.data.title}
                  </h2>
                  <button
                    onClick={closeModal}
                    className="text-gray-400 hover:text-gray-600 p-1"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>

                <div className="space-y-3 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>{modal.data.time}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>{modal.data.location}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <span>{modal.data.attendees} attendees</span>
                  </div>
                </div>

                <div className="mt-6 flex justify-end gap-2">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50"
                  >
                    Close
                  </button>
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-sm font-medium text-white bg-google-blue rounded hover:bg-blue-600"
                  >
                    Edit Event
                  </button>
                </div>
              </div>
            )}

            {modal.type === 'permission-denied' && (
              <div className="p-6">
                <div className="flex items-start gap-4 mb-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                      <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                  </div>

                  <div className="flex-1">
                    <h2 className="text-lg font-semibold text-gray-900 mb-2">
                      Permission Denied
                    </h2>
                    <p className="text-sm text-gray-600">
                      {modal.data.reason}
                    </p>
                  </div>

                  <button
                    onClick={closeModal}
                    className="text-gray-400 hover:text-gray-600 p-1"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-sm font-medium text-white bg-gray-600 rounded hover:bg-gray-700"
                  >
                    OK
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default SimulatedPopups;
