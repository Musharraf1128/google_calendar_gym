import { useState, useRef } from 'react';

const EVENT_COLORS = [
  { bg: 'bg-blue-100', border: 'border-blue-500', text: 'text-blue-900' },
  { bg: 'bg-green-100', border: 'border-green-500', text: 'text-green-900' },
  { bg: 'bg-red-100', border: 'border-red-500', text: 'text-red-900' },
  { bg: 'bg-yellow-100', border: 'border-yellow-500', text: 'text-yellow-900' },
  { bg: 'bg-purple-100', border: 'border-purple-500', text: 'text-purple-900' },
  { bg: 'bg-pink-100', border: 'border-pink-500', text: 'text-pink-900' },
  { bg: 'bg-indigo-100', border: 'border-indigo-500', text: 'text-indigo-900' },
  { bg: 'bg-orange-100', border: 'border-orange-500', text: 'text-orange-900' },
];

function EventCard({ event, onClick, onDragStart, onResizeEnd, currentDay }) {
  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [resizeStartY, setResizeStartY] = useState(0);
  const [initialDuration, setInitialDuration] = useState(0);
  const cardRef = useRef(null);

  const start = new Date(event.start);
  const end = new Date(event.end);

  // If currentDay is provided, calculate duration only for this day
  let visibleStart = start;
  let visibleEnd = end;

  if (currentDay) {
    const dayStart = new Date(currentDay.getFullYear(), currentDay.getMonth(), currentDay.getDate(), 0, 0, 0);
    const dayEnd = new Date(currentDay.getFullYear(), currentDay.getMonth(), currentDay.getDate(), 23, 59, 59, 999);

    // Clamp to this day's boundaries
    visibleStart = start > dayStart ? start : dayStart;
    visibleEnd = end < dayEnd ? end : dayEnd;
  }

  const duration = (visibleEnd - visibleStart) / (1000 * 60); // Duration in minutes

  // Calculate height based on duration (1 hour = 48px)
  const height = Math.max((duration / 60) * 48, 20);

  // Calculate top position based on minutes within the hour
  const minutes = visibleStart.getMinutes();
  const topOffset = (minutes / 60) * 48; // 48px per hour

  // Get color based on event color property or fallback to ID-based color
  const colorIndex = event.color_id ? parseInt(event.color_id) : parseInt(event.id.split('-')[0], 16) % EVENT_COLORS.length;
  const color = EVENT_COLORS[colorIndex % EVENT_COLORS.length];

  function formatTime(date) {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  function handleResizeStart(e) {
    e.stopPropagation();
    e.preventDefault();

    setIsResizing(true);
    setResizeStartY(e.clientY);
    setInitialDuration(end - start);

    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeStop);
  }

  function handleResizeMove(e) {
    if (!isResizing) return;

    const deltaY = e.clientY - resizeStartY;
    const deltaMinutes = Math.round((deltaY / 48) * 60); // 48px = 1 hour
    const newDuration = Math.max(initialDuration + deltaMinutes * 60 * 1000, 15 * 60 * 1000); // Minimum 15 minutes

    if (cardRef.current) {
      const newHeight = Math.max((newDuration / (1000 * 60 * 60)) * 48, 20);
      cardRef.current.style.height = `${newHeight}px`;
    }
  }

  function handleResizeStop(e) {
    if (!isResizing) return;

    const deltaY = e.clientY - resizeStartY;
    const deltaMinutes = Math.round((deltaY / 48) * 60);
    const newDuration = Math.max(initialDuration + deltaMinutes * 60 * 1000, 15 * 60 * 1000);

    setIsResizing(false);
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeStop);

    if (onResizeEnd && Math.abs(deltaMinutes) >= 15) {
      onResizeEnd(newDuration);
    }
  }

  function handleDragStartInternal(e) {
    setIsDragging(true);
    if (onDragStart) {
      onDragStart(e, event);
    }
  }

  function handleDragEnd(e) {
    setIsDragging(false);
  }

  function handleClick(e) {
    e.stopPropagation();
    if (onClick) {
      onClick(e);
    }
  }

  return (
    <div
      ref={cardRef}
      draggable={!isResizing}
      onDragStart={handleDragStartInternal}
      onDragEnd={handleDragEnd}
      onClick={handleClick}
      className={`absolute inset-x-1 ${color.bg} ${color.border} ${color.text} border-l-4 rounded p-1 cursor-move hover:shadow-md transition-all overflow-hidden group ${
        isDragging ? 'opacity-50 shadow-lg scale-105' : ''
      }`}
      style={{ height: `${height}px`, top: `${topOffset}px` }}
      data-automation-id={`event-${event.id}`}
      data-event-title={event.summary}
    >
      <div className="text-xs font-medium truncate" title={event.summary}>
        {event.summary}
      </div>
      {duration >= 30 && (
        <div className="text-xs opacity-75 truncate">
          {formatTime(visibleStart)}
        </div>
      )}
      {event.location && duration >= 60 && (
        <div className="text-xs opacity-60 truncate">
          📍 {event.location}
        </div>
      )}

      {/* Resize handle */}
      <div
        className="absolute bottom-0 left-0 right-0 h-2 cursor-ns-resize opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
        onMouseDown={handleResizeStart}
        data-automation-id={`resize-handle-${event.id}`}
      >
        <div className="w-8 h-1 bg-gray-500 rounded"></div>
      </div>
    </div>
  );
}

export default EventCard;
