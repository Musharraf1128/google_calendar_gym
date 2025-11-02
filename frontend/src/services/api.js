/**
 * API Service for Google Calendar Gym
 *
 * Provides functions to interact with the backend API
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Users API
export const getUsers = async () => {
  const response = await api.get('/users');
  return response.data;
};

export const getUserById = async (userId) => {
  const response = await api.get(`/users/${userId}`);
  return response.data;
};

// Calendars API
export const getCalendars = async () => {
  const response = await api.get('/calendars');
  return response.data;
};

export const getUserCalendars = async (userId) => {
  const response = await api.get(`/users/${userId}/calendars`);
  return response.data;
};

export const createCalendar = async (calendarData) => {
  const response = await api.post('/calendars', calendarData);
  return response.data;
};

// Events API
export const getCalendarEvents = async (calendarId, params = {}) => {
  const response = await api.get(`/calendars/${calendarId}/events`, { params });
  return response.data;
};

export const getEvent = async (eventId) => {
  const response = await api.get(`/events/${eventId}`);
  return response.data;
};

export const createEvent = async (calendarId, eventData) => {
  const response = await api.post(`/calendars/${calendarId}/events`, eventData);
  return response.data;
};

export const updateEvent = async (eventId, eventData) => {
  const response = await api.patch(`/events/${eventId}`, eventData);
  return response.data;
};

export const deleteEvent = async (eventId) => {
  const response = await api.delete(`/events/${eventId}`);
  return response.data;
};

// Event Attendees API
export const getEventAttendees = async (eventId) => {
  const response = await api.get(`/events/${eventId}/attendees`);
  return response.data;
};

export const updateAttendeeResponse = async (eventId, attendeeId, responseStatus) => {
  const response = await api.patch(`/events/${eventId}/attendees/${attendeeId}`, {
    response_status: responseStatus,
  });
  return response.data;
};

// Tasks API
export const getUserTasks = async (userId, params = {}) => {
  const response = await api.get(`/users/${userId}/tasks`, { params });
  return response.data;
};

export const getTask = async (taskId) => {
  const response = await api.get(`/tasks/${taskId}`);
  return response.data;
};

export const createTask = async (taskData) => {
  const response = await api.post('/tasks', taskData);
  return response.data;
};

export const updateTask = async (taskId, taskData) => {
  const response = await api.patch(`/tasks/${taskId}`, taskData);
  return response.data;
};

export const deleteTask = async (taskId) => {
  const response = await api.delete(`/tasks/${taskId}`);
  return response.data;
};

export const toggleTaskCompletion = async (taskId) => {
  const response = await api.post(`/tasks/${taskId}/toggle`);
  return response.data;
};

export const getEventTasks = async (eventId) => {
  const response = await api.get(`/events/${eventId}/tasks`);
  return response.data;
};

export default api;
