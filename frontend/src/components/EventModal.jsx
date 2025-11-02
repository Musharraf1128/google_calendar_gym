import { useState, useEffect } from 'react';

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
  });

  const [errors, setErrors] = useState({});

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
      });
    }
  }, [event, initialSlot]);

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

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
      data-automation-id="event-modal-overlay"
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        data-automation-id="event-modal"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-normal text-gray-900">
            {event ? 'Edit Event' : 'New Event'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            data-automation-id="close-modal-button"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="px-6 py-4 space-y-4">
            {/* Title */}
            <div>
              <input
                type="text"
                value={formData.summary}
                onChange={(e) => handleChange('summary', e.target.value)}
                placeholder="Add title"
                className={`w-full px-3 py-2 border ${
                  errors.summary ? 'border-red-500' : 'border-gray-300'
                } rounded-md focus:outline-none focus:ring-2 focus:ring-google-blue focus:border-transparent`}
                data-automation-id="event-title-input"
              />
              {errors.summary && (
                <p className="mt-1 text-sm text-red-600">{errors.summary}</p>
              )}
            </div>

            {/* Color Picker */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Event Color
              </label>
              <div className="flex gap-2 flex-wrap">
                {EVENT_COLORS.map((color) => (
                  <button
                    key={color.id}
                    type="button"
                    onClick={() => handleChange('color_id', color.id)}
                    className={`w-8 h-8 rounded-full ${color.bg} transition-all ${
                      formData.color_id === color.id
                        ? 'ring-2 ring-offset-2 ring-gray-400 scale-110'
                        : 'hover:scale-105'
                    }`}
                    title={color.name}
                    data-automation-id={`color-${color.id}`}
                  />
                ))}
              </div>
            </div>

            {/* Start Time */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Time
              </label>
              <input
                type="datetime-local"
                value={formData.start}
                onChange={(e) => handleChange('start', e.target.value)}
                className={`w-full px-3 py-2 border ${
                  errors.start ? 'border-red-500' : 'border-gray-300'
                } rounded-md focus:outline-none focus:ring-2 focus:ring-google-blue focus:border-transparent`}
                data-automation-id="event-start-input"
              />
              {errors.start && (
                <p className="mt-1 text-sm text-red-600">{errors.start}</p>
              )}
            </div>

            {/* End Time */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Time
              </label>
              <input
                type="datetime-local"
                value={formData.end}
                onChange={(e) => handleChange('end', e.target.value)}
                className={`w-full px-3 py-2 border ${
                  errors.end ? 'border-red-500' : 'border-gray-300'
                } rounded-md focus:outline-none focus:ring-2 focus:ring-google-blue focus:border-transparent`}
                data-automation-id="event-end-input"
              />
              {errors.end && (
                <p className="mt-1 text-sm text-red-600">{errors.end}</p>
              )}
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => handleChange('location', e.target.value)}
                placeholder="Add location"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-google-blue focus:border-transparent"
                data-automation-id="event-location-input"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Add description"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-google-blue focus:border-transparent resize-none"
                data-automation-id="event-description-input"
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div>
              {onDelete && (
                <button
                  type="button"
                  onClick={onDelete}
                  className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                  data-automation-id="delete-event-button"
                >
                  Delete
                </button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-md transition-colors"
                data-automation-id="cancel-button"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-6 py-2 bg-google-blue text-white rounded-md hover:bg-google-blue-hover transition-colors"
                data-automation-id="save-event-button"
              >
                Save
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EventModal;
