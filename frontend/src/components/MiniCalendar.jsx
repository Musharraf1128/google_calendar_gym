import { useState } from 'react';

const DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function MiniCalendar({ selectedDate, onDateSelect }) {
  const [currentMonth, setCurrentMonth] = useState(new Date());

  function getDaysInMonth(date) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days = [];

    // Add empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }

    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(new Date(year, month, day));
    }

    return days;
  }

  function handlePrevMonth() {
    const newMonth = new Date(currentMonth);
    newMonth.setMonth(newMonth.getMonth() - 1);
    setCurrentMonth(newMonth);
  }

  function handleNextMonth() {
    const newMonth = new Date(currentMonth);
    newMonth.setMonth(newMonth.getMonth() + 1);
    setCurrentMonth(newMonth);
  }

  function isToday(date) {
    if (!date) return false;
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  function isSelected(date) {
    if (!date || !selectedDate) return false;
    return date.toDateString() === selectedDate.toDateString();
  }

  const days = getDaysInMonth(currentMonth);

  return (
    <div className="bg-white p-4" data-automation-id="mini-calendar">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-900">
          {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
        </span>
        <div className="flex gap-1">
          <button
            onClick={handlePrevMonth}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
            data-automation-id="mini-cal-prev-month"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </button>
          <button
            onClick={handleNextMonth}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
            data-automation-id="mini-cal-next-month"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {DAYS.map((day, index) => (
          <div key={index} className="text-center text-xs text-gray-600 font-medium h-6 flex items-center justify-center">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar days */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day, index) => (
          <div key={index} className="aspect-square">
            {day ? (
              <button
                onClick={() => onDateSelect(day)}
                className={`w-full h-full flex items-center justify-center text-xs rounded-full transition-colors ${
                  isToday(day)
                    ? 'bg-google-blue text-white font-medium'
                    : isSelected(day)
                    ? 'bg-blue-100 text-google-blue font-medium'
                    : 'hover:bg-gray-100 text-gray-900'
                }`}
                data-automation-id={`mini-cal-day-${day.getDate()}`}
              >
                {day.getDate()}
              </button>
            ) : (
              <div />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default MiniCalendar;
