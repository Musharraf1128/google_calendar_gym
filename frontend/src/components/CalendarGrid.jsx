import { useState, useRef } from 'react';
import EventCard from './EventCard';

const HOURS = Array.from({ length: 24 }, (_, i) => i);
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

function CalendarGrid({ weekStart, events, tasks = [], onSlotClick, onEventClick, onEventUpdate, onToggleTask, numDays = 7 }) {
  const [draggedEvent, setDraggedEvent] = useState(null);
  const [resizingEvent, setResizingEvent] = useState(null);
  const gridRef = useRef(null);

  // Generate numDays days starting from weekStart
  const weekDays = Array.from({ length: numDays }, (_, i) => {
    const date = new Date(weekStart);
    date.setDate(weekStart.getDate() + i);
    return date;
  });

  function handleSlotClick(day, hour) {
    // Create a new date using the day's year, month, and date to avoid timezone issues
    const start = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour, 0, 0, 0);
    const end = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour + 1, 0, 0, 0);

    onSlotClick({
      start: start.toISOString(),
      end: end.toISOString(),
    });
  }

  function getEventsForDayAndHour(day, hour) {
    return events.filter(event => {
      const eventStart = new Date(event.start);
      const eventEnd = new Date(event.end);

      // Get the start of this day
      const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 0, 0, 0);
      const dayEnd = new Date(day.getFullYear(), day.getMonth(), day.getDate(), 23, 59, 59);

      // Check if event overlaps with this day
      if (eventStart > dayEnd || eventEnd <= dayStart) {
        return false; // Event doesn't touch this day at all
      }

      // Determine the first hour this event should appear in this day
      let firstHourInDay;
      if (eventStart >= dayStart) {
        // Event starts on this day - use its actual start hour
        firstHourInDay = eventStart.getHours();
      } else {
        // Event started before this day - show it starting at midnight (hour 0)
        firstHourInDay = 0;
      }

      // Only show the event in its first hour on this day
      return hour === firstHourInDay;
    });
  }

  function getTasksForDayAndHour(day, hour) {
    // Tasks appear at their due time on the calendar grid
    return tasks.filter(task => {
      if (!task.due) return false; // Only show tasks with due dates
      const taskDue = new Date(task.due);

      // Check if task is due on this day
      if (taskDue.toDateString() !== day.toDateString()) {
        return false;
      }

      // Show task at its due hour
      return taskDue.getHours() === hour;
    });
  }

  function getItemsForDayAndHour(day, hour) {
    const eventsInSlot = getEventsForDayAndHour(day, hour);
    const tasksInSlot = getTasksForDayAndHour(day, hour);

    // Combine events and tasks, marking tasks with a type
    return [
      ...eventsInSlot.map(e => ({ ...e, itemType: 'event' })),
      ...tasksInSlot.map(t => ({ ...t, itemType: 'task' }))
    ];
  }

  function formatTime(hour) {
    if (hour === 0) return '12 AM';
    if (hour < 12) return `${hour} AM`;
    if (hour === 12) return '12 PM';
    return `${hour - 12} PM`;
  }

  function isToday(date) {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }

  function handleDragStart(event, eventData) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', eventData.id);
    setDraggedEvent(eventData);
  }

  function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }

  function handleDrop(event, day, hour) {
    event.preventDefault();
    event.stopPropagation();

    if (!draggedEvent) return;

    // Calculate the exact drop position within the hour
    const rect = event.currentTarget.getBoundingClientRect();
    const y = event.clientY - rect.top;
    const cellHeight = rect.height;
    const minutesOffset = Math.round((y / cellHeight) * 60);

    // CRITICAL: Backend stores times in UTC
    // draggedEvent.start and draggedEvent.end are UTC ISO strings
    // We need to preserve the LOCAL time the user intends

    // Get original times (these are UTC ISO strings from backend)
    const oldStartUtc = new Date(draggedEvent.start);
    const oldEndUtc = new Date(draggedEvent.end);
    const duration = oldEndUtc - oldStartUtc;

    // Create new time in LOCAL timezone
    // The user dragged to hour:minutesOffset in their local time
    const newStartLocal = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour, minutesOffset, 0, 0);
    const newEndLocal = new Date(newStartLocal.getTime() + duration);

    // Convert to UTC ISO strings for backend
    const newStartUtc = newStartLocal.toISOString();
    const newEndUtc = newEndLocal.toISOString();

    // DIAGNOSTIC LOGGING
    console.group('🔄 Event Drag & Drop - CalendarGrid');
    console.log('Original event:', draggedEvent);
    console.log('---');
    console.log('OLD Start (UTC from backend):', draggedEvent.start);
    console.log('  → Parsed as Date:', oldStartUtc.toString());
    console.log('  → Local time:', oldStartUtc.toLocaleString());
    console.log('  → UTC ISO:', oldStartUtc.toISOString());
    console.log('---');
    console.log('NEW Start (intended local time):', `${hour}:${minutesOffset.toString().padStart(2, '0')}`);
    console.log('  → Created Date:', newStartLocal.toString());
    console.log('  → Local time:', newStartLocal.toLocaleString());
    console.log('  → Will send to backend (UTC):', newStartUtc);
    console.log('---');
    console.log('Timezone offset (hours):', -new Date().getTimezoneOffset() / 60);
    console.log('Hour difference:', newStartLocal.getHours() - new Date(newStartUtc).getHours());
    console.groupEnd();

    onEventUpdate(draggedEvent.id, {
      start: newStartUtc,
      end: newEndUtc,
    });

    setDraggedEvent(null);
  }

  return (
    <div className="bg-white" data-automation-id="calendar-grid">
      <div className={`grid border-l border-t border-gray-300`} style={{ gridTemplateColumns: `60px repeat(${numDays}, 1fr)` }}>
        {/* Empty corner cell */}
        <div className="border-r border-b border-gray-300 bg-white sticky top-0 z-20"></div>

        {/* Day headers */}
        {weekDays.map((day, index) => (
          <div
            key={index}
            className="border-r border-b border-gray-300 bg-white sticky top-0 z-20 p-2 text-center"
            data-automation-id={`day-header-${index}`}
          >
            <div className="text-xs text-gray-600 font-medium uppercase">
              {DAYS[day.getDay()].substring(0, 3)}
            </div>
            <div
              className={`text-2xl mt-1 ${
                isToday(day)
                  ? 'w-10 h-10 mx-auto rounded-full bg-google-blue text-white flex items-center justify-center'
                  : 'text-gray-900'
              }`}
            >
              {day.getDate()}
            </div>
          </div>
        ))}

        {/* Time slots */}
        {HOURS.map((hour) => (
          <div key={hour} className="contents">
            {/* Time label */}
            <div
              className="border-r border-b border-gray-300 bg-gray-50 p-2 text-right text-xs text-gray-600 sticky left-0 z-10"
              data-automation-id={`time-label-${hour}`}
            >
              {formatTime(hour)}
            </div>

            {/* Day slots */}
            {weekDays.map((day, dayIndex) => {
              const itemsInSlot = getItemsForDayAndHour(day, hour);

              return (
                <div
                  key={dayIndex}
                  className="border-r border-b border-gray-300 h-12 relative cursor-pointer"
                  onClick={() => handleSlotClick(day, hour)}
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, day, hour)}
                  data-automation-id={`time-slot-${dayIndex}-${hour}`}
                >
                  {itemsInSlot.map((item) => {
                    if (item.itemType === 'task') {
                      // Render task with checkbox
                      return (
                        <div
                          key={item.id}
                          className="absolute top-0 left-0 right-0 p-1 bg-blue-50 border-l-2 border-blue-500 hover:bg-blue-100 transition-colors cursor-pointer z-10"
                          onClick={(e) => {
                            e.stopPropagation();
                            onEventClick(item, e); // Reuse event click handler for tasks
                          }}
                          data-automation-id={`task-${item.id}`}
                        >
                          <div className="flex items-start gap-1">
                            <input
                              type="checkbox"
                              checked={item.status === 'completed'}
                              onChange={(e) => {
                                e.stopPropagation();
                                onToggleTask(item.id);
                              }}
                              className="mt-0.5 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <span className={`text-xs font-medium ${item.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                              {item.title}
                            </span>
                          </div>
                        </div>
                      );
                    } else {
                      // Render event normally
                      return (
                        <EventCard
                          key={item.id}
                          event={item}
                          currentDay={day}
                          onClick={(e) => {
                            onEventClick(item, e);
                          }}
                          onDragStart={handleDragStart}
                          onResizeEnd={(newDuration) => {
                            const start = new Date(item.start);
                            const end = new Date(start.getTime() + newDuration);
                            onEventUpdate(item.id, {
                              start: item.start,
                              end: end.toISOString(),
                            });
                          }}
                        />
                      );
                    }
                  })}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default CalendarGrid;
