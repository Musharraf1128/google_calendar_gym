import { useState } from 'react';
import EventCard from './EventCard';

const HOURS = Array.from({ length: 24 }, (_, i) => i);

function DayView({ selectedDate, events, tasks = [], onSlotClick, onEventClick, onEventUpdate, onToggleTask }) {
  const [draggedEvent, setDraggedEvent] = useState(null);

  function handleSlotClick(hour) {
    // Create a new date using the selected date's year, month, and date to avoid timezone issues
    const start = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate(), hour, 0, 0, 0);
    const end = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate(), hour + 1, 0, 0, 0);

    onSlotClick({
      start: start.toISOString(),
      end: end.toISOString(),
    });
  }

  function getEventsForHour(hour) {
    return events.filter(event => {
      const eventStart = new Date(event.start);
      const eventDay = eventStart.toDateString();
      const eventHour = eventStart.getHours();

      return eventDay === selectedDate.toDateString() && eventHour === hour;
    });
  }

  function getTasksForDay() {
    return tasks.filter(task => {
      if (!task.due) return false; // Only show tasks with due dates
      const taskDue = new Date(task.due);
      return taskDue.toDateString() === selectedDate.toDateString();
    });
  }

  function formatTime(hour) {
    if (hour === 0) return '12 AM';
    if (hour < 12) return `${hour} AM`;
    if (hour === 12) return '12 PM';
    return `${hour - 12} PM`;
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

  function handleDrop(event, hour) {
    event.preventDefault();
    event.stopPropagation();

    if (!draggedEvent) return;

    // Calculate the exact drop position within the hour
    const rect = event.currentTarget.getBoundingClientRect();
    const y = event.clientY - rect.top;
    const cellHeight = rect.height;
    const minutesOffset = Math.round((y / cellHeight) * 60);

    // CRITICAL: Backend stores times in UTC
    // Get original times (UTC ISO strings from backend)
    const oldStartUtc = new Date(draggedEvent.start);
    const oldEndUtc = new Date(draggedEvent.end);
    const duration = oldEndUtc - oldStartUtc;

    // Create new time in LOCAL timezone
    const newStartLocal = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate(), hour, minutesOffset, 0, 0);
    const newEndLocal = new Date(newStartLocal.getTime() + duration);

    // Convert to UTC ISO strings for backend
    const newStartUtc = newStartLocal.toISOString();
    const newEndUtc = newEndLocal.toISOString();

    // DIAGNOSTIC LOGGING
    console.group('🔄 Event Drag & Drop - DayView');
    console.log('Original event:', draggedEvent);
    console.log('---');
    console.log('OLD Start (UTC from backend):', draggedEvent.start);
    console.log('  → Parsed as Date:', oldStartUtc.toString());
    console.log('  → Local time:', oldStartUtc.toLocaleString());
    console.log('---');
    console.log('NEW Start (intended local time):', `${hour}:${minutesOffset.toString().padStart(2, '0')}`);
    console.log('  → Created Date:', newStartLocal.toString());
    console.log('  → Local time:', newStartLocal.toLocaleString());
    console.log('  → Will send to backend (UTC):', newStartUtc);
    console.log('---');
    console.log('Timezone offset (hours):', -new Date().getTimezoneOffset() / 60);
    console.groupEnd();

    onEventUpdate(draggedEvent.id, {
      start: newStartUtc,
      end: newEndUtc,
    });

    setDraggedEvent(null);
  }

  const dayTasks = getTasksForDay();

  return (
    <div className="bg-white" data-automation-id="day-view">
      <div className="grid grid-cols-[80px_1fr]">
        {/* Time slots */}
        {HOURS.map((hour) => {
          const eventsInSlot = getEventsForHour(hour);

          return (
            <div key={hour} className="contents">
              {/* Time label */}
              <div className="border-r border-b border-gray-200 p-2 text-right text-xs text-gray-600 bg-gray-50">
                {formatTime(hour)}
              </div>

              {/* Hour slot */}
              <div
                className="border-r border-b border-gray-200 h-12 relative cursor-pointer"
                onClick={() => handleSlotClick(hour)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, hour)}
                data-automation-id={`day-slot-${hour}`}
              >
                {eventsInSlot.map((event) => (
                  <EventCard
                    key={event.id}
                    event={event}
                    currentDay={selectedDate}
                    onClick={(e) => {
                      onEventClick(event, e);
                    }}
                    onDragStart={handleDragStart}
                    onResizeEnd={(newDuration) => {
                      const start = new Date(event.start);
                      const end = new Date(start.getTime() + newDuration);
                      onEventUpdate(event.id, {
                        start: event.start,
                        end: end.toISOString(),
                      });
                    }}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Tasks section */}
      {dayTasks.length > 0 && (
        <div className="border-t-2 border-gray-300 mt-4">
          <div className="px-4 py-3">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Tasks</h3>
            <div className="space-y-2">
              {dayTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded transition-colors"
                  data-automation-id={`task-${task.id}`}
                >
                  <input
                    type="checkbox"
                    checked={task.status === 'completed'}
                    onChange={() => onToggleTask && onToggleTask(task.id)}
                    className="mt-1 w-4 h-4 text-google-blue border-gray-300 rounded focus:ring-google-blue cursor-pointer"
                    data-automation-id={`task-checkbox-${task.id}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm ${task.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-900'}`}>
                      {task.title}
                    </div>
                    {task.notes && (
                      <div className="text-xs text-gray-600 mt-1">{task.notes}</div>
                    )}
                    {task.due && (
                      <div className="text-xs text-gray-500 mt-1">
                        Due: {new Date(task.due).toLocaleTimeString('en-US', {
                          hour: 'numeric',
                          minute: '2-digit',
                          hour12: true
                        })}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DayView;
