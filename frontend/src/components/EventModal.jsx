import { useState, useEffect, useRef } from 'react';

const EVENT_COLORS = [
  { id: 0, bg: 'bg-blue-500', name: 'Blue' },
  { id: 1, bg: 'bg-green-500', name: 'Green' },
  { id: 2, bg: 'bg-red-500', name: 'Red' },
  { id: 3, bg: 'bg-yellow-500', name: 'Yellow' },
  { id: 4, bg: 'bg-purple-500', name: 'Purple' },
  { id: 5, bg: 'bg-pink-500', name: 'Pink' },
  { id: 6, bg: 'bg-indigo-500', name: 'Indigo' },
  { id: 7, bg: 'bg-orange-500', name: 'Orange' },
];

function EventModal({ event, initialSlot, onSave, onDelete, onClose }) {
  const [formData, setFormData] = useState({
    summary: '',
    description: '',
    location: '',
    start: '',
    end: '',
    color_id: 0,
    repeat: 'none',
  });

  const [errors, setErrors] = useState({});
  const [showRepeatDropdown, setShowRepeatDropdown] = useState(false);
  const repeatDropdownRef = useRef(null);

  useEffect(() => {
    if (event) {
      // Edit existing event
      setFormData({
        summary: event.summary || '',
        description: event.description || '',
        location: event.location || '',
        start: formatDateTimeLocal(event.start),
        end: formatDateTimeLocal(event.end),
        color_id: event.color_id || 0,
        repeat: 'none',
      });
    } else if (initialSlot) {
      // New event from slot click
      setFormData({
        summary: '',
        description: '',
        location: '',
        start: formatDateTimeLocal(initialSlot.start),
        end: formatDateTimeLocal(initialSlot.end),
        color_id: 0,
        repeat: 'none',
      });
    } else {
      // New event from "Create" button
      const now = new Date();
      now.setMinutes(0, 0, 0);
      const oneHourLater = new Date(now.getTime() + 60 * 60 * 1000);

      setFormData({
        summary: '',
        description: '',
        location: '',
        start: formatDateTimeLocal(now),
        end: formatDateTimeLocal(oneHourLater),
        color_id: 0,
        repeat: 'none',
      });
    }
  }, [event, initialSlot]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (repeatDropdownRef.current && !repeatDropdownRef.current.contains(event.target)) {
        setShowRepeatDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function formatDateTimeLocal(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  function validateForm() {
    const newErrors = {};

    if (!formData.summary.trim()) {
      newErrors.summary = 'Title is required';
    }

    if (!formData.start) {
      newErrors.start = 'Start time is required';
    }

    if (!formData.end) {
      newErrors.end = 'End time is required';
    }

    if (formData.start && formData.end) {
      const start = new Date(formData.start);
      const end = new Date(formData.end);

      if (end <= start) {
        newErrors.end = 'End time must be after start time';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit(e) {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // CRITICAL: formData.start and formData.end are from datetime-local input
    // Format: "YYYY-MM-DDTHH:MM" in LOCAL timezone
    // We need to convert to UTC ISO strings for backend

    const startLocal = new Date(formData.start);
    const endLocal = new Date(formData.end);

    const startUtc = startLocal.toISOString();
    const endUtc = endLocal.toISOString();

    // DIAGNOSTIC LOGGING
    console.group('💾 Event Save - EventModal');
    console.log('Form data (datetime-local format):');
    console.log('  Start:', formData.start);
    console.log('  End:', formData.end);
    console.log('---');
    console.log('Parsed as Date objects (LOCAL timezone):');
    console.log('  Start:', startLocal.toString());
    console.log('  Start local:', startLocal.toLocaleString());
    console.log('  End:', endLocal.toString());
    console.log('  End local:', endLocal.toLocaleString());
    console.log('---');
    console.log('Converting to UTC for backend:');
    console.log('  Start UTC:', startUtc);
    console.log('  End UTC:', endUtc);
    console.log('---');
    console.log('Timezone offset (hours):', -new Date().getTimezoneOffset() / 60);
    console.groupEnd();

    const eventData = {
      summary: formData.summary,
      description: formData.description,
      location: formData.location,
      start: startUtc,
      end: endUtc,
      is_all_day: false,
      color_id: formData.color_id,
    };

    onSave(eventData);
  }

  function handleChange(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  }

  function getRepeatText() {
    switch(formData.repeat) {
      case 'daily': return 'Daily';
      case 'weekly': return 'Weekly';
      case 'monthly': return 'Monthly';
      case 'weekdays': return 'Every weekday (Mon-Fri)';
      default: return 'Does not repeat';
    }
  }

  function handleRepeatSelect(option) {
    handleChange('repeat', option);
    setShowRepeatDropdown(false);
  }

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-30 flex items-start justify-center z-50 p-4 pt-20"
      onClick={onClose}
      data-automation-id="event-modal-overlay"
    >
      <div
        className="bg-white rounded-lg shadow-2xl max-w-xl w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        data-automation-id="event-modal"
      >
        {/* Header with icons */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2">
            {/* Color dot indicator */}
            <div className={`w-6 h-6 rounded-full ${EVENT_COLORS[formData.color_id]?.bg || 'bg-blue-500'}`} />
            {onDelete && (
              <button
                type="button"
                onClick={onDelete}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                data-automation-id="delete-event-button"
                title="Delete event"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            data-automation-id="close-modal-button"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-160px)]">
          <div className="px-6 py-4 space-y-4">
            {/* Title - Google Calendar style */}
            <div>
              <input
                type="text"
                value={formData.summary}
                onChange={(e) => handleChange('summary', e.target.value)}
                placeholder="Add title"
                className={`w-full px-0 py-3 text-xl border-0 border-b-2 ${
                  errors.summary ? 'border-red-500' : 'border-transparent hover:border-gray-300 focus:border-google-blue'
                } focus:outline-none transition-colors`}
                data-automation-id="event-title-input"
                autoFocus
              />
              {errors.summary && (
                <p className="mt-1 text-sm text-red-600">{errors.summary}</p>
              )}
            </div>

            {/* Start Time - with icon */}
            <div className="flex items-center gap-3 py-3 border-b border-gray-200 hover:bg-gray-50 transition-colors">
              <svg className="w-6 h-6 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <input
                  type="datetime-local"
                  value={formData.start}
                  onChange={(e) => handleChange('start', e.target.value)}
                  className={`w-full bg-transparent border-0 focus:outline-none ${
                    errors.start ? 'text-red-600' : 'text-gray-700'
                  } text-sm`}
                  data-automation-id="event-start-input"
                />
                {errors.start && (
                  <p className="text-xs text-red-600 mt-1">{errors.start}</p>
                )}
              </div>
            </div>

            {/* End Time - with icon */}
            <div className="flex items-center gap-3 py-3 border-b border-gray-200 hover:bg-gray-50 transition-colors">
              <svg className="w-6 h-6 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <input
                  type="datetime-local"
                  value={formData.end}
                  onChange={(e) => handleChange('end', e.target.value)}
                  className={`w-full bg-transparent border-0 focus:outline-none ${
                    errors.end ? 'text-red-600' : 'text-gray-700'
                  } text-sm`}
                  data-automation-id="event-end-input"
                />
                {errors.end && (
                  <p className="text-xs text-red-600 mt-1">{errors.end}</p>
                )}
              </div>
            </div>

            {/* Does not repeat - with functional dropdown */}
            <div className="relative" ref={repeatDropdownRef}>
              <button
                type="button"
                onClick={() => setShowRepeatDropdown(!showRepeatDropdown)}
                className="w-full flex items-center gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors text-left border-b border-gray-200"
              >
                <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="flex-1 text-gray-700 text-sm">{getRepeatText()}</span>
                <svg className={`w-5 h-5 text-gray-400 transition-transform ${showRepeatDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Repeat Dropdown */}
              {showRepeatDropdown && (
                <div className="absolute left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1">
                  <button
                    type="button"
                    onClick={() => handleRepeatSelect('none')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      formData.repeat === 'none' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                  >
                    Does not repeat
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRepeatSelect('daily')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      formData.repeat === 'daily' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                  >
                    Daily
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRepeatSelect('weekdays')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      formData.repeat === 'weekdays' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                  >
                    Every weekday (Mon-Fri)
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRepeatSelect('weekly')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      formData.repeat === 'weekly' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                  >
                    Weekly
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRepeatSelect('monthly')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      formData.repeat === 'monthly' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                  >
                    Monthly
                  </button>
                </div>
              )}
            </div>

            {/* Location - with icon */}
            <div className="flex items-center gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors border-b border-gray-200">
              <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => handleChange('location', e.target.value)}
                placeholder="Add location"
                className="flex-1 bg-transparent border-0 focus:outline-none text-gray-700 text-sm placeholder-gray-400"
                data-automation-id="event-location-input"
              />
            </div>

            {/* Description - with icon */}
            <div className="flex items-start gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors">
              <svg className="w-5 h-5 text-gray-500 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
              </svg>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Add description"
                rows={3}
                className="flex-1 bg-transparent border-0 focus:outline-none text-gray-700 text-sm resize-none placeholder-gray-400"
                data-automation-id="event-description-input"
              />
            </div>

            {/* Color Picker - compact */}
            <div className="flex items-center gap-3 py-3">
              <svg className="w-6 h-6 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
              </svg>
              <div className="flex gap-2 flex-wrap flex-1">
                {EVENT_COLORS.map((color) => (
                  <button
                    key={color.id}
                    type="button"
                    onClick={() => handleChange('color_id', color.id)}
                    className={`w-7 h-7 rounded-full ${color.bg} transition-all ${
                      formData.color_id === color.id
                        ? 'ring-2 ring-offset-1 ring-gray-400 scale-110'
                        : 'hover:scale-105 opacity-70 hover:opacity-100'
                    }`}
                    title={color.name}
                    data-automation-id={`color-${color.id}`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Footer - Save button only */}
          <div className="flex items-center justify-end px-6 py-4 bg-white border-t border-gray-200">
            <button
              type="submit"
              className="px-8 py-2 bg-google-blue text-white rounded hover:bg-blue-600 transition-colors font-medium"
              data-automation-id="save-event-button"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EventModal;
