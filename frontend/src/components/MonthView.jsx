import { useState } from 'react';

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function MonthView({ currentMonth, events, onDateClick, onEventClick }) {
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

  function getEventsForDay(day) {
    if (!day) return [];
    return events.filter(event => {
      const eventStart = new Date(event.start);
      return eventStart.toDateString() === day.toDateString();
    });
  }

  function isToday(date) {
    if (!date) return false;
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  function formatEventTime(event) {
    const start = new Date(event.start);
    return start.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  const days = getDaysInMonth(currentMonth);

  return (
    <div className="h-full bg-white" data-automation-id="month-view">
      {/* Day headers */}
      <div className="grid grid-cols-7 border-b border-gray-300">
        {DAYS.map((day) => (
          <div
            key={day}
            className="border-r border-gray-300 p-2 text-center text-xs font-medium text-gray-600 uppercase bg-white"
          >
            {day.substring(0, 3)}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 auto-rows-fr h-[calc(100%-3rem)]">
        {days.map((day, index) => {
          const dayEvents = getEventsForDay(day);

          return (
            <div
              key={index}
              className={`border-r border-b border-gray-300 p-1 cursor-pointer hover:bg-gray-50 transition-colors overflow-hidden ${
                !day ? 'bg-gray-50' : ''
              }`}
              onClick={() => day && onDateClick(day)}
              data-automation-id={day ? `month-day-${day.getDate()}` : 'month-empty'}
            >
              {day && (
                <>
                  <div
                    className={`text-sm mb-1 ${
                      isToday(day)
                        ? 'w-6 h-6 rounded-full bg-google-blue text-white flex items-center justify-center font-medium'
                        : 'text-gray-900 pl-1'
                    }`}
                  >
                    {day.getDate()}
                  </div>
                  <div className="space-y-1">
                    {dayEvents.slice(0, 3).map((event) => (
                      <div
                        key={event.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          onEventClick(event, e);
                        }}
                        className="text-xs bg-google-blue text-white px-1 py-0.5 rounded truncate hover:bg-google-blue-hover transition-colors"
                        title={`${formatEventTime(event)} ${event.summary}`}
                      >
                        {formatEventTime(event)} {event.summary}
                      </div>
                    ))}
                    {dayEvents.length > 3 && (
                      <div className="text-xs text-gray-600 px-1">
                        +{dayEvents.length - 3} more
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default MonthView;
