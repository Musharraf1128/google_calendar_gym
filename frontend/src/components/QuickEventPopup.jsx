import { useEffect, useRef } from 'react';

const EVENT_COLORS = [
  { bg: 'bg-blue-500', text: 'Blue' },
  { bg: 'bg-green-500', text: 'Green' },
  { bg: 'bg-red-500', text: 'Red' },
  { bg: 'bg-yellow-500', text: 'Yellow' },
  { bg: 'bg-purple-500', text: 'Purple' },
  { bg: 'bg-pink-500', text: 'Pink' },
  { bg: 'bg-indigo-500', text: 'Indigo' },
  { bg: 'bg-orange-500', text: 'Orange' },
];

function QuickEventPopup({ event, position, onEdit, onDelete, onClose }) {
  const popupRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (popupRef.current && !popupRef.current.contains(e.target)) {
        onClose();
      }
    }

    function handleEscape(e) {
      if (e.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  }

  const colorIndex = event.color_id ? parseInt(event.color_id) : parseInt(event.id.split('-')[0], 16) % EVENT_COLORS.length;
  const eventColor = EVENT_COLORS[colorIndex % EVENT_COLORS.length];

  return (
    <div
      ref={popupRef}
      className="fixed bg-white rounded-lg shadow-2xl border border-gray-200 z-50 w-80"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      data-automation-id="quick-event-popup"
    >
      {/* Color bar */}
      <div className={`h-2 ${eventColor.bg} rounded-t-lg`}></div>

      <div className="p-4">
        {/* Header with close button */}
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-lg font-medium text-gray-900 pr-2" title={event.summary}>
            {event.summary}
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors flex-shrink-0"
            data-automation-id="quick-popup-close"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Event details */}
        <div className="space-y-2 mb-4">
          {/* Date and time */}
          <div className="flex items-start gap-2 text-sm text-gray-700">
            <svg className="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <div>{formatDate(event.start)}</div>
              <div className="text-gray-600">
                {formatTime(event.start)} - {formatTime(event.end)}
              </div>
            </div>
          </div>

          {/* Location */}
          {event.location && (
            <div className="flex items-start gap-2 text-sm text-gray-700">
              <svg className="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <div>{event.location}</div>
            </div>
          )}

          {/* Description */}
          {event.description && (
            <div className="flex items-start gap-2 text-sm text-gray-700">
              <svg className="w-5 h-5 text-gray-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
              </svg>
              <div className="line-clamp-3">{event.description}</div>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <button
            onClick={onDelete}
            className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors"
            data-automation-id="quick-delete-button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
          <button
            onClick={onEdit}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-google-blue text-white rounded-md hover:bg-google-blue-hover transition-colors"
            data-automation-id="quick-edit-button"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit
          </button>
        </div>
      </div>
    </div>
  );
}

export default QuickEventPopup;
