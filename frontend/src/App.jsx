import { useState, useEffect } from 'react';
import CalendarGrid from './components/CalendarGrid';
import DayView from './components/DayView';
import MonthView from './components/MonthView';
import MiniCalendar from './components/MiniCalendar';
import EventModal from './components/EventModal';
import TaskModal from './components/TaskModal';
import QuickEventPopup from './components/QuickEventPopup';
import SimulatedPopups from './components/SimulatedPopups';
import TasksView from './components/TasksView';
import {
  getUsers,
  getUserCalendars,
  getCalendarEvents,
  createEvent,
  updateEvent,
  deleteEvent,
  getUserTasks,
  createTask,
  updateTask,
  deleteTask,
  toggleTaskCompletion
} from './services/api';

function App() {
  // Check if simulated popups are enabled via environment variable
  const simulatePopups = import.meta.env.VITE_SIMULATE_POPUPS === 'true';
  // User management
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [showUserSelect, setShowUserSelect] = useState(true);

  // Calendar and events
  const [calendars, setCalendars] = useState([]);
  const [selectedCalendar, setSelectedCalendar] = useState(null);
  const [events, setEvents] = useState([]);

  // Tasks
  const [tasks, setTasks] = useState([]);

  // Modal state
  const [showEventModal, setShowEventModal] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [modalInitialSlot, setModalInitialSlot] = useState(null);

  // Task modal state
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskInitialDate, setTaskInitialDate] = useState(null);

  // Create button dropdown
  const [showCreateDropdown, setShowCreateDropdown] = useState(false);

  // Quick popup state
  const [showQuickPopup, setShowQuickPopup] = useState(false);
  const [quickPopupEvent, setQuickPopupEvent] = useState(null);
  const [quickPopupPosition, setQuickPopupPosition] = useState({ x: 0, y: 0 });

  // View state
  const [currentView, setCurrentView] = useState('week'); // 'day', 'week', 'month', '4days'
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [currentWeekStart, setCurrentWeekStart] = useState(getWeekStart(new Date()));
  const [showViewDropdown, setShowViewDropdown] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showTasksView, setShowTasksView] = useState(false);

  // Load users on mount
  useEffect(() => {
    loadUsers();
  }, []);

  // Load calendars when user selected
  useEffect(() => {
    if (currentUser) {
      loadCalendars();
    }
  }, [currentUser]);

  // Load events when calendar selected
  useEffect(() => {
    if (selectedCalendar) {
      loadEvents();
    }
  }, [selectedCalendar]);

  // Load tasks when user selected
  useEffect(() => {
    if (currentUser) {
      loadTasks();
    }
  }, [currentUser]);

  function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day; // Get Sunday
    return new Date(d.setDate(diff));
  }

  async function loadUsers() {
    try {
      const data = await getUsers();
      setUsers(data);

      // Check for saved user
      const savedUser = sessionStorage.getItem('calendar_user');
      if (savedUser) {
        const user = JSON.parse(savedUser);
        setCurrentUser(user);
        setShowUserSelect(false);
      }
    } catch (error) {
      console.error('Error loading users:', error);
    }
  }

  async function loadCalendars() {
    try {
      const data = await getUserCalendars(currentUser.id);
      setCalendars(data);
      if (data.length > 0) {
        setSelectedCalendar(data[0].calendar);
      }
    } catch (error) {
      console.error('Error loading calendars:', error);
      // If user not found (404), clear session and show user select
      if (error.response && error.response.status === 404) {
        console.warn('User not found. Clearing session...');
        sessionStorage.removeItem('calendar_user');
        setCurrentUser(null);
        setShowUserSelect(true);
        alert('Your session has expired or the user no longer exists. Please select a user again.');
      }
    }
  }

  async function loadEvents() {
    try {
      const data = await getCalendarEvents(selectedCalendar.id, { expand_recurring: false });
      setEvents(data);
    } catch (error) {
      console.error('Error loading events:', error);
    }
  }

  async function loadTasks() {
    try {
      const data = await getUserTasks(currentUser.id);
      setTasks(data);
    } catch (error) {
      console.error('Error loading tasks:', error);
    }
  }

  function handleUserSelect(user) {
    setCurrentUser(user);
    sessionStorage.setItem('calendar_user', JSON.stringify(user));
    setShowUserSelect(false);
  }

  function handleLogout() {
    setCurrentUser(null);
    setSelectedCalendar(null);
    setEvents([]);
    sessionStorage.removeItem('calendar_user');
    setShowUserSelect(true);
  }

  function handleCreateEvent(slot) {
    setSelectedEvent(null);
    setModalInitialSlot(slot);
    setShowEventModal(true);
  }

  function handleEditEvent(event, position) {
    // Check if it's a task - if so, open task modal instead
    if (event.itemType === 'task') {
      setSelectedTask(event);
      setTaskInitialDate(null);
      setShowTaskModal(true);
      return;
    }

    // Show quick popup when clicking on an event
    setQuickPopupEvent(event);

    // Calculate popup position
    if (position && position.clientX && position.clientY) {
      const x = Math.min(position.clientX, window.innerWidth - 350); // Keep within viewport
      const y = Math.min(position.clientY, window.innerHeight - 400);
      setQuickPopupPosition({ x, y });
    } else {
      // Fallback to center if no position provided
      setQuickPopupPosition({
        x: window.innerWidth / 2 - 160,
        y: window.innerHeight / 2 - 200
      });
    }

    setShowQuickPopup(true);
  }

  function handleQuickPopupEdit() {
    // Close quick popup and open full modal
    setSelectedEvent(quickPopupEvent);
    setModalInitialSlot(null);
    setShowQuickPopup(false);
    setShowEventModal(true);
  }

  function handleQuickPopupClose() {
    setShowQuickPopup(false);
    setQuickPopupEvent(null);
  }

  async function handleSaveEvent(eventData) {
    try {
      const payload = {
        ...eventData,
        calendar_id: selectedCalendar.id,
        status: 'confirmed',
      };

      if (selectedEvent) {
        // Update existing event
        await updateEvent(selectedEvent.id, payload);
      } else {
        // Create new event
        await createEvent(selectedCalendar.id, payload);
      }

      setShowEventModal(false);
      setSelectedEvent(null);
      setModalInitialSlot(null);
      loadEvents();
    } catch (error) {
      console.error('Error saving event:', error);
      alert('Failed to save event: ' + (error.response?.data?.detail || error.message));
    }
  }

  async function handleDeleteEvent(eventId) {
    if (!confirm('Are you sure you want to delete this event?')) return;

    try {
      await deleteEvent(eventId);
      setShowEventModal(false);
      setShowQuickPopup(false);
      setSelectedEvent(null);
      setQuickPopupEvent(null);
      loadEvents();
    } catch (error) {
      console.error('Error deleting event:', error);
      alert('Failed to delete event');
    }
  }

  async function handleQuickDeleteEvent() {
    if (quickPopupEvent) {
      await handleDeleteEvent(quickPopupEvent.id);
    }
  }

  async function handleEventUpdate(eventId, updates) {
    try {
      await updateEvent(eventId, updates);
      loadEvents();
    } catch (error) {
      console.error('Error updating event:', error);
      alert('Failed to update event');
    }
  }

  // Task handlers
  function handleCreateTask(initialDate = null) {
    setSelectedTask(null);
    setTaskInitialDate(initialDate);
    setShowTaskModal(true);
  }

  async function handleSaveTask(taskData) {
    try {
      const payload = {
        ...taskData,
        user_id: currentUser.id,
      };

      if (selectedTask) {
        // Update existing task
        await updateTask(selectedTask.id, payload);
      } else {
        // Create new task
        await createTask(payload);
      }

      setShowTaskModal(false);
      setSelectedTask(null);
      setTaskInitialDate(null);
      loadTasks();
    } catch (error) {
      console.error('Error saving task:', error);
      alert('Failed to save task: ' + (error.response?.data?.detail || error.message));
    }
  }

  async function handleDeleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
      await deleteTask(taskId);
      setShowTaskModal(false);
      setSelectedTask(null);
      loadTasks();
    } catch (error) {
      console.error('Error deleting task:', error);
      alert('Failed to delete task');
    }
  }

  async function handleToggleTask(taskId) {
    try {
      await toggleTaskCompletion(taskId);
      loadTasks();
    } catch (error) {
      console.error('Error toggling task:', error);
      alert('Failed to toggle task completion');
    }
  }

  function handlePrevWeek() {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() - 7);
    setCurrentWeekStart(newStart);
  }

  function handleNextWeek() {
    const newStart = new Date(currentWeekStart);
    newStart.setDate(newStart.getDate() + 7);
    setCurrentWeekStart(newStart);
  }

  function handleToday() {
    const today = new Date();
    setSelectedDate(today);
    setCurrentWeekStart(getWeekStart(today));
  }

  function handlePrev() {
    if (currentView === 'day') {
      const newDate = new Date(selectedDate);
      newDate.setDate(newDate.getDate() - 1);
      setSelectedDate(newDate);
      setCurrentWeekStart(getWeekStart(newDate));
    } else if (currentView === 'week') {
      handlePrevWeek();
    } else if (currentView === '4days') {
      const newStart = new Date(currentWeekStart);
      newStart.setDate(newStart.getDate() - 4);
      setCurrentWeekStart(newStart);
      setSelectedDate(newStart);
    } else if (currentView === 'month') {
      const newDate = new Date(selectedDate);
      newDate.setMonth(newDate.getMonth() - 1);
      setSelectedDate(newDate);
    }
  }

  function handleNext() {
    if (currentView === 'day') {
      const newDate = new Date(selectedDate);
      newDate.setDate(newDate.getDate() + 1);
      setSelectedDate(newDate);
      setCurrentWeekStart(getWeekStart(newDate));
    } else if (currentView === 'week') {
      handleNextWeek();
    } else if (currentView === '4days') {
      const newStart = new Date(currentWeekStart);
      newStart.setDate(newStart.getDate() + 4);
      setCurrentWeekStart(newStart);
      setSelectedDate(newStart);
    } else if (currentView === 'month') {
      const newDate = new Date(selectedDate);
      newDate.setMonth(newDate.getMonth() + 1);
      setSelectedDate(newDate);
    }
  }

  function handleMiniCalendarDateSelect(date) {
    setSelectedDate(date);
    setCurrentWeekStart(getWeekStart(date));
    if (currentView === 'month') {
      setCurrentView('day');
    }
  }

  function getDateRangeText() {
    if (currentView === 'day') {
      return selectedDate.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
      });
    } else if (currentView === 'week' || currentView === '4days') {
      const numDays = currentView === 'week' ? 7 : 4;
      const endDate = new Date(currentWeekStart);
      endDate.setDate(currentWeekStart.getDate() + numDays - 1);

      if (currentWeekStart.getMonth() === endDate.getMonth()) {
        return `${currentWeekStart.toLocaleDateString('en-US', { month: 'long' })} ${currentWeekStart.getDate()} - ${endDate.getDate()}, ${currentWeekStart.getFullYear()}`;
      } else {
        return `${currentWeekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}, ${currentWeekStart.getFullYear()}`;
      }
    } else if (currentView === 'month') {
      return selectedDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    }
  }

  function getViewLabel() {
    switch(currentView) {
      case 'day': return 'Day';
      case '4days': return '4 Days';
      case 'week': return 'Week';
      case 'month': return 'Month';
      default: return 'Week';
    }
  }

  function handleViewSelect(view) {
    setCurrentView(view);
    setShowViewDropdown(false);
  }

  function handleSearch() {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const query = searchQuery.toLowerCase();

    // Search events
    const matchedEvents = events.filter(event =>
      event.summary?.toLowerCase().includes(query) ||
      event.description?.toLowerCase().includes(query) ||
      event.location?.toLowerCase().includes(query)
    );

    // Search tasks
    const matchedTasks = tasks.filter(task =>
      task.title?.toLowerCase().includes(query) ||
      task.notes?.toLowerCase().includes(query)
    );

    setSearchResults([
      ...matchedEvents.map(e => ({ ...e, type: 'event' })),
      ...matchedTasks.map(t => ({ ...t, type: 'task' }))
    ]);
  }

  function handleSearchClose() {
    setShowSearch(false);
    setSearchQuery('');
    setSearchResults([]);
  }

  function handleSearchResultClick(result) {
    if (result.type === 'event') {
      handleEditEvent(result);
    } else {
      setSelectedTask(result);
      setTaskInitialDate(null);
      setShowTaskModal(true);
    }
    handleSearchClose();
  }

  // User selection screen
  if (showUserSelect) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full" data-automation-id="user-select-screen">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-normal text-gray-900 mb-2">Google Calendar Gym</h1>
            <p className="text-gray-600">Select a user to continue</p>
          </div>

          <div className="space-y-2">
            {users.map((user) => (
              <button
                key={user.id}
                onClick={() => handleUserSelect(user)}
                className="w-full flex items-center gap-3 p-4 rounded-lg border border-gray-300 hover:bg-gray-50 hover:border-google-blue transition-colors"
                data-automation-id={`user-select-${user.email}`}
              >
                <div className="w-10 h-10 rounded-full bg-google-blue text-white flex items-center justify-center font-medium">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 text-left">
                  <div className="font-medium text-gray-900">{user.name}</div>
                  <div className="text-sm text-gray-600">{user.email}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Main calendar view
  return (
    <div className="h-screen bg-white flex flex-col" data-automation-id="calendar-app">
      {/* Header */}
      <header className="flex-none border-b border-gray-300 bg-white">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <img
                src="https://www.gstatic.com/images/branding/product/1x/calendar_2020q4_48dp.png"
                alt="Calendar"
                className="w-10 h-10"
              />
              <h1 className="text-xl text-gray-700 font-normal">Calendar</h1>
            </div>

            <button
              onClick={handleToday}
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
              data-automation-id="today-button"
            >
              Today
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={handlePrev}
                className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                data-automation-id="prev-button"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </button>
              <button
                onClick={handleNext}
                className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                data-automation-id="next-button"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
              </button>
            </div>

            <span className="text-lg text-gray-900" data-automation-id="current-date-display">
              {getDateRangeText()}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {/* Search Icon - only show in calendar view */}
            {!showTasksView && (
              <button
                onClick={() => setShowSearch(!showSearch)}
                className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                data-automation-id="search-button"
                title="Search"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
            )}

            {/* View selector dropdown - only show in calendar view */}
            {!showTasksView && (
            <div className="relative">
              <button
                onClick={() => setShowViewDropdown(!showViewDropdown)}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                data-automation-id="view-dropdown-button"
              >
                <span className="text-sm text-gray-700">{getViewLabel()}</span>
                <svg className={`w-4 h-4 text-gray-600 transition-transform ${showViewDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Dropdown menu */}
              {showViewDropdown && (
                <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-300 rounded-lg shadow-lg z-50">
                  <button
                    onClick={() => handleViewSelect('day')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      currentView === 'day' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                    data-automation-id="view-day"
                  >
                    Day
                  </button>
                  <button
                    onClick={() => handleViewSelect('4days')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      currentView === '4days' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                    data-automation-id="view-4days"
                  >
                    4 Days
                  </button>
                  <button
                    onClick={() => handleViewSelect('week')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      currentView === 'week' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                    data-automation-id="view-week"
                  >
                    Week
                  </button>
                  <button
                    onClick={() => handleViewSelect('month')}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 transition-colors ${
                      currentView === 'month' ? 'bg-blue-50 text-google-blue font-medium' : 'text-gray-700'
                    }`}
                    data-automation-id="view-month"
                  >
                    Month
                  </button>
                </div>
              )}
            </div>
            )}

            {/* Calendar/Tasks Segmented Control */}
            <div className="flex border border-gray-300 rounded overflow-hidden">
              <button
                onClick={() => setShowTasksView(false)}
                className={`px-4 py-1.5 text-sm transition-colors flex items-center gap-2 ${
                  !showTasksView
                    ? 'bg-google-blue text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                data-automation-id="calendar-view-button"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span>Calendar</span>
              </button>
              <button
                onClick={() => setShowTasksView(true)}
                className={`px-4 py-1.5 text-sm border-l border-gray-300 transition-colors flex items-center gap-2 ${
                  showTasksView
                    ? 'bg-google-blue text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
                data-automation-id="tasks-view-button"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                <span>Tasks</span>
              </button>
            </div>

            <div className="relative">
              <button
                onClick={handleLogout}
                className="w-8 h-8 rounded-full bg-google-blue text-white flex items-center justify-center font-medium"
                data-automation-id="user-menu-button"
                title={currentUser.name}
              >
                {currentUser.name.charAt(0).toUpperCase()}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content with sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Fixed, no scrolling - Only show in calendar view */}
        {!showTasksView && (
        <aside className="flex-none w-64 border-r border-gray-300 bg-white flex flex-col overflow-y-auto">
          {/* Create button with dropdown */}
          <div className="p-4 relative">
            <button
              onClick={() => setShowCreateDropdown(!showCreateDropdown)}
              className="w-full flex items-center gap-3 px-6 py-3 bg-white border border-gray-300 rounded-full hover:bg-gray-50 hover:shadow-md transition-all"
              data-automation-id="create-button"
            >
              <svg className="w-5 h-5 text-google-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="text-sm font-medium text-gray-700">Create</span>
            </button>

            {/* Dropdown Menu */}
            {showCreateDropdown && (
              <div
                className="absolute top-full left-4 right-4 mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-50"
                data-automation-id="create-dropdown"
              >
                <button
                  onClick={() => {
                    handleCreateEvent(null);
                    setShowCreateDropdown(false);
                  }}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center gap-3"
                  data-automation-id="create-event-option"
                >
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span className="text-sm font-medium text-gray-700">Event</span>
                </button>
                <button
                  onClick={() => {
                    handleCreateTask(null);
                    setShowCreateDropdown(false);
                  }}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center gap-3 border-t border-gray-200"
                  data-automation-id="create-task-option"
                >
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                  <span className="text-sm font-medium text-gray-700">Task</span>
                </button>
              </div>
            )}
          </div>

          {/* Mini Calendar */}
          <div className="border-t border-gray-200">
            <MiniCalendar
              selectedDate={selectedDate}
              onDateSelect={handleMiniCalendarDateSelect}
            />
          </div>
        </aside>
        )}

        {/* Calendar Grid - Scrollable frame on the right */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden bg-white">
          {showTasksView ? (
            /* Tasks View */
            <TasksView
              tasks={tasks}
              onToggleTask={handleToggleTask}
              onTaskClick={(task) => {
                setSelectedTask(task);
                setTaskInitialDate(null);
                setShowTaskModal(true);
              }}
              onCreateTask={handleCreateTask}
            />
          ) : (
            /* Calendar View */
            selectedCalendar ? (
              <>
                {currentView === 'day' && (
                  <DayView
                    selectedDate={selectedDate}
                    events={events}
                    tasks={tasks}
                    onSlotClick={handleCreateEvent}
                    onEventClick={handleEditEvent}
                    onEventUpdate={handleEventUpdate}
                    onToggleTask={handleToggleTask}
                  />
                )}
                {currentView === 'week' && (
                  <CalendarGrid
                    weekStart={currentWeekStart}
                    events={events}
                    tasks={tasks}
                    onSlotClick={handleCreateEvent}
                    onEventClick={handleEditEvent}
                    onEventUpdate={handleEventUpdate}
                    onToggleTask={handleToggleTask}
                    numDays={7}
                  />
                )}
                {currentView === '4days' && (
                  <CalendarGrid
                    weekStart={currentWeekStart}
                    events={events}
                    tasks={tasks}
                    onSlotClick={handleCreateEvent}
                    onEventClick={handleEditEvent}
                    onEventUpdate={handleEventUpdate}
                    onToggleTask={handleToggleTask}
                    numDays={4}
                  />
                )}
                {currentView === 'month' && (
                  <MonthView
                    currentMonth={selectedDate}
                    events={events}
                    onDateClick={handleMiniCalendarDateSelect}
                    onEventClick={handleEditEvent}
                  />
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">No calendar selected</p>
              </div>
            )
          )}
        </main>
      </div>

      {/* Quick Event Popup */}
      {showQuickPopup && quickPopupEvent && (
        <QuickEventPopup
          event={quickPopupEvent}
          position={quickPopupPosition}
          onEdit={handleQuickPopupEdit}
          onDelete={handleQuickDeleteEvent}
          onClose={handleQuickPopupClose}
        />
      )}

      {/* Event Modal */}
      {showEventModal && (
        <EventModal
          event={selectedEvent}
          initialSlot={modalInitialSlot}
          onSave={handleSaveEvent}
          onDelete={selectedEvent ? () => handleDeleteEvent(selectedEvent.id) : null}
          onClose={() => {
            setShowEventModal(false);
            setSelectedEvent(null);
            setModalInitialSlot(null);
          }}
        />
      )}

      {/* Task Modal */}
      {showTaskModal && (
        <TaskModal
          task={selectedTask}
          initialDate={taskInitialDate}
          onSave={handleSaveTask}
          onDelete={selectedTask ? () => handleDeleteTask(selectedTask.id) : null}
          onClose={() => {
            setShowTaskModal(false);
            setSelectedTask(null);
            setTaskInitialDate(null);
          }}
        />
      )}

      {/* Search Modal */}
      {showSearch && (
        <div className="fixed inset-0 bg-black bg-opacity-30 z-50 flex items-start justify-center pt-16">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl mx-4">
            {/* Search Header */}
            <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (e.target.value.trim()) {
                    handleSearch();
                  } else {
                    setSearchResults([]);
                  }
                }}
                placeholder="Search"
                className="flex-1 text-lg border-0 focus:outline-none"
                autoFocus
                data-automation-id="search-input"
              />
              <button
                onClick={handleSearchClose}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Search Results */}
            <div className="max-h-96 overflow-y-auto">
              {searchQuery.trim() === '' ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  Start typing to search for events and tasks
                </div>
              ) : searchResults.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  No results found for "{searchQuery}"
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {searchResults.map((result, index) => (
                    <button
                      key={`${result.type}-${result.id}-${index}`}
                      onClick={() => handleSearchResultClick(result)}
                      className="w-full px-6 py-4 text-left hover:bg-gray-50 transition-colors flex items-start gap-3"
                      data-automation-id={`search-result-${index}`}
                    >
                      {result.type === 'event' ? (
                        <>
                          <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900">{result.summary}</div>
                            {result.start && (
                              <div className="text-sm text-gray-600 mt-1">
                                {new Date(result.start).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric',
                                  hour: 'numeric',
                                  minute: '2-digit'
                                })}
                              </div>
                            )}
                            {result.location && (
                              <div className="text-sm text-gray-500 mt-1">{result.location}</div>
                            )}
                          </div>
                        </>
                      ) : (
                        <>
                          <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                          </svg>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900">{result.title}</div>
                            {result.due && (
                              <div className="text-sm text-gray-600 mt-1">
                                Due: {new Date(result.due).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric',
                                  hour: 'numeric',
                                  minute: '2-digit'
                                })}
                              </div>
                            )}
                            {result.notes && (
                              <div className="text-sm text-gray-500 mt-1 truncate">{result.notes}</div>
                            )}
                          </div>
                        </>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Simulated Popups - for testing/demo purposes */}
      <SimulatedPopups enabled={simulatePopups} />
    </div>
  );
}

export default App;
