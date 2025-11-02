import { useState } from 'react';

function TasksView({ tasks, onToggleTask, onTaskClick, onCreateTask }) {
  const [selectedList, setSelectedList] = useState('all');

  // Group tasks by status or create task lists
  const taskLists = [
    { id: 'all', name: 'All tasks', icon: '✓' },
    { id: 'starred', name: 'Starred', icon: '★' },
  ];

  // Additional lists - in a real app these would be user-created
  const customLists = [
    { id: 'routine', name: 'Routine' },
    { id: 'personal', name: 'Personal' },
    { id: 'shopping', name: 'Shopping' },
    { id: 'wishlist', name: 'Wishlist' },
    { id: 'work', name: 'Work' },
  ];

  // Filter tasks based on selected list
  function getFilteredTasks() {
    if (selectedList === 'all') {
      return tasks;
    } else if (selectedList === 'starred') {
      // For now, return empty - would need starred field in task model
      return [];
    } else {
      // For custom lists, show all tasks (in real app, tasks would have list_id)
      return tasks;
    }
  }

  const filteredTasks = getFilteredTasks();
  const completedTasks = filteredTasks.filter(t => t.status === 'completed');
  const incompleteTasks = filteredTasks.filter(t => t.status !== 'completed');

  return (
    <div className="flex h-full bg-white">
      {/* Left Sidebar */}
      <aside className="w-64 border-r border-gray-300 flex flex-col">
        {/* Main Lists */}
        <div className="py-4">
          {taskLists.map(list => (
            <button
              key={list.id}
              onClick={() => setSelectedList(list.id)}
              className={`w-full px-6 py-3 text-left flex items-center gap-3 transition-colors ${
                selectedList === list.id
                  ? 'bg-blue-50 text-google-blue border-r-4 border-google-blue'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              data-automation-id={`task-list-${list.id}`}
            >
              <span className="text-lg">{list.icon}</span>
              <span className="font-normal">{list.name}</span>
            </button>
          ))}
        </div>

        {/* Lists Section */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-6 py-2">
            <button className="flex items-center gap-2 text-gray-600 text-sm">
              <span>Lists</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {customLists.map(list => (
            <button
              key={list.id}
              onClick={() => setSelectedList(list.id)}
              className={`w-full px-6 py-2 text-left flex items-center justify-between transition-colors ${
                selectedList === list.id
                  ? 'bg-blue-50 text-google-blue'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
              data-automation-id={`custom-list-${list.id}`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={true}
                  readOnly
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-sm">{list.name}</span>
              </div>
              <span className="text-xs text-gray-500">{filteredTasks.length}</span>
            </button>
          ))}

          {/* Create new list button */}
          <button className="w-full px-6 py-3 text-left flex items-center gap-2 text-gray-700 hover:bg-gray-50 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="text-sm">Create new list</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200">
          <h1 className="text-2xl font-normal text-gray-900 capitalize">
            {taskLists.find(l => l.id === selectedList)?.name ||
             customLists.find(l => l.id === selectedList)?.name ||
             'Tasks'}
          </h1>
        </div>

        {/* Tasks List */}
        <div className="px-8 py-6">
          {/* Add Task Button */}
          <button
            onClick={() => onCreateTask(null)}
            className="flex items-center gap-3 px-4 py-3 text-gray-700 hover:bg-gray-50 rounded transition-colors w-full text-left mb-4"
            data-automation-id="add-task-button"
          >
            <svg className="w-5 h-5 text-google-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add a task</span>
          </button>

          {/* Incomplete Tasks */}
          {incompleteTasks.length > 0 && (
            <div className="space-y-2 mb-8">
              {incompleteTasks.map(task => (
                <div
                  key={task.id}
                  className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 rounded transition-colors cursor-pointer"
                  onClick={() => onTaskClick(task)}
                  data-automation-id={`task-item-${task.id}`}
                >
                  <input
                    type="checkbox"
                    checked={false}
                    onChange={(e) => {
                      e.stopPropagation();
                      onToggleTask(task.id);
                    }}
                    className="mt-1 w-5 h-5 text-google-blue border-gray-300 rounded focus:ring-google-blue cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-gray-900">{task.title}</div>
                    {task.due && (
                      <div className="flex items-center gap-1 mt-1 text-sm text-gray-600">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <span>
                          {new Date(task.due).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit'
                          })}
                        </span>
                      </div>
                    )}
                    {task.notes && (
                      <div className="text-sm text-gray-500 mt-1">{task.notes}</div>
                    )}
                  </div>
                  <button
                    className="p-1 opacity-0 hover:opacity-100 focus:opacity-100 hover:bg-gray-200 rounded transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      // Star functionality would go here
                    }}
                  >
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Completed Tasks */}
          {completedTasks.length > 0 && (
            <div>
              <button className="flex items-center gap-2 px-4 py-2 text-gray-600 text-sm hover:bg-gray-50 rounded w-full text-left mb-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
                <span>Completed ({completedTasks.length})</span>
              </button>
              <div className="space-y-2">
                {completedTasks.map(task => (
                  <div
                    key={task.id}
                    className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 rounded transition-colors cursor-pointer opacity-60"
                    onClick={() => onTaskClick(task)}
                    data-automation-id={`completed-task-${task.id}`}
                  >
                    <input
                      type="checkbox"
                      checked={true}
                      onChange={(e) => {
                        e.stopPropagation();
                        onToggleTask(task.id);
                      }}
                      className="mt-1 w-5 h-5 text-google-blue border-gray-300 rounded focus:ring-google-blue cursor-pointer"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-gray-600 line-through">{task.title}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {incompleteTasks.length === 0 && completedTasks.length === 0 && (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-24 h-24 mb-4">
                <svg className="w-full h-full text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="text-lg font-normal text-gray-900 mb-2">No tasks yet</h3>
              <p className="text-gray-600 text-sm">
                Add your to-dos and keep track of them across Google Workspace
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default TasksView;
