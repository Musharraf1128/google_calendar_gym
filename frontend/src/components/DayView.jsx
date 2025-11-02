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

  function getTasksForHour(hour) {
    return tasks.filter(task => {
      if (!task.due) return false; // Only show tasks with due dates
      const taskDue = new Date(task.due);
      return taskDue.toDateString() === selectedDate.toDateString() && taskDue.getHours() === hour;
    });
  }

  function getItemsForHour(hour) {
    const eventsInSlot = getEventsForHour(hour);
    const tasksInSlot = getTasksForHour(hour);

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

  return (
    <div className="bg-white" data-automation-id="day-view">
      <div className="grid grid-cols-[80px_1fr]">
        {/* Time slots */}
        {HOURS.map((hour) => {
          const itemsInSlot = getItemsForHour(hour);

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
                {itemsInSlot.map((item) => {
                  if (item.itemType === 'task') {
                    // Render task with checkbox
                    return (
                      <div
                        key={item.id}
                        className="absolute top-0 left-0 right-0 p-1 bg-blue-50 border-l-2 border-blue-500 hover:bg-blue-100 transition-colors cursor-pointer z-10"
                        onClick={(e) => {
                          e.stopPropagation();
                          onEventClick(item, e);
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
                        currentDay={selectedDate}
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
            </div>
          );
        })}
      </div>

    </div>
  );
}

export default DayView;
