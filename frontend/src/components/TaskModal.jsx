import { useState, useEffect, useRef } from 'react';

function TaskModal({ task, initialDate, onSave, onDelete, onClose }) {
  const [formData, setFormData] = useState({
    title: '',
    notes: '',
    due: '',
    repeat: 'none', // none, daily, weekly, monthly
  });

  const [errors, setErrors] = useState({});
  const [showRepeatDropdown, setShowRepeatDropdown] = useState(false);
  const [showAllDayToggle, setShowAllDayToggle] = useState(false);
  const repeatDropdownRef = useRef(null);

  useEffect(() => {
    if (task) {
      // Edit existing task
      setFormData({
        title: task.title || '',
        notes: task.notes || '',
        due: task.due ? formatDateTimeLocal(task.due) : '',
        repeat: 'none', // Tasks don't have recurrence in backend yet
      });
    } else if (initialDate) {
      // New task with initial date
      setFormData({
        title: '',
        notes: '',
        due: formatDateTimeLocal(initialDate),
        repeat: 'none',
      });
    } else {
      // New task without initial date
      setFormData({
        title: '',
        notes: '',
        due: '',
        repeat: 'none',
      });
    }
  }, [task, initialDate]);

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

  function formatDateForDisplay(dateString) {
    if (!dateString) return 'Add date/time';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
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

  function validateForm() {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleSubmit(e) {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Convert due date to UTC if provided
    let dueUtc = null;
    if (formData.due) {
      const dueLocal = new Date(formData.due);
      dueUtc = dueLocal.toISOString();
    }

    const taskData = {
      title: formData.title,
      notes: formData.notes || null,
      due: dueUtc,
      status: task ? task.status : 'needsAction',
    };

    onSave(taskData);
  }

  function handleChange(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
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
      data-automation-id="task-modal-overlay"
    >
      <div
        className="bg-white rounded-lg shadow-2xl max-w-xl w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        data-automation-id="task-modal"
      >
        {/* Header with icons */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-2">
            {onDelete && (
              <button
                type="button"
                onClick={onDelete}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                data-automation-id="delete-task-button"
                title="Delete task"
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
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-1">
            {/* Title - Google Calendar style (no border, just underline on focus) */}
            <div className="mb-4">
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Add title"
                className={`w-full px-0 py-3 text-xl font-normal border-0 border-b-2 ${
                  errors.title ? 'border-red-500' : 'border-transparent hover:border-gray-300 focus:border-google-blue'
                } focus:outline-none transition-colors placeholder-gray-400`}
                data-automation-id="task-title-input"
                autoFocus
              />
              {errors.title && (
                <p className="mt-1 text-sm text-red-600">{errors.title}</p>
              )}
            </div>

            {/* Due Date/Time - with icon */}
            <div className="group">
              <label className="flex items-center gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors cursor-pointer">
                <svg className="w-5 h-5 text-gray-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <input
                  type="datetime-local"
                  value={formData.due}
                  onChange={(e) => handleChange('due', e.target.value)}
                  className="flex-1 bg-transparent border-0 focus:outline-none text-gray-700 text-sm cursor-pointer"
                  data-automation-id="task-due-input"
                />
              </label>
            </div>

            {/* Does not repeat - with functional dropdown */}
            <div className="relative group" ref={repeatDropdownRef}>
              <button
                type="button"
                onClick={() => setShowRepeatDropdown(!showRepeatDropdown)}
                className="w-full flex items-center gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors text-left"
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

            {/* Description - with icon */}
            <div className="group pt-2">
              <div className="flex items-start gap-3 py-3 px-2 -mx-2 rounded hover:bg-gray-50 transition-colors">
                <svg className="w-5 h-5 text-gray-500 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                </svg>
                <textarea
                  value={formData.notes}
                  onChange={(e) => handleChange('notes', e.target.value)}
                  placeholder="Add description"
                  rows={3}
                  className="flex-1 bg-transparent border-0 focus:outline-none text-gray-700 text-sm resize-none placeholder-gray-400"
                  data-automation-id="task-notes-input"
                />
              </div>
            </div>
          </div>

          {/* Footer - Save button only */}
          <div className="flex items-center justify-end px-6 py-4 bg-white border-t border-gray-200">
            <button
              type="submit"
              className="px-8 py-2 bg-google-blue text-white rounded hover:bg-blue-600 transition-colors font-medium text-sm"
              data-automation-id="save-task-button"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default TaskModal;
