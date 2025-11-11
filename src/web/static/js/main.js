// Multi-Agent Collaboration System - Frontend JavaScript

// WebSocket connection for real-time updates
let ws = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Multi-Agent System initialized');
    initWebSocket();
    setupEventListeners();
});

// Setup WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('WebSocket connected');
            showNotification('Connected to server', 'success');
        };
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
            showNotification('Connection error', 'danger');
        };
        
        ws.onclose = function() {
            console.log('WebSocket disconnected');
            showNotification('Disconnected from server', 'warning');
            // Attempt to reconnect after 5 seconds
            setTimeout(initWebSocket, 5000);
        };
    } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
    }
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    console.log('Received message:', data);
    
    switch(data.type) {
        case 'task_update':
            updateTaskStatus(data.payload);
            break;
        case 'agent_status':
            updateAgentStatus(data.payload);
            break;
        case 'notification':
            showNotification(data.message, data.level);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

// Update task status in the UI
function updateTaskStatus(task) {
    const taskElement = document.getElementById(`task-${task.id}`);
    if (taskElement) {
        taskElement.querySelector('.status-badge').textContent = task.status;
        taskElement.querySelector('.status-badge').className = `status-badge status-${task.status.toLowerCase()}`;
    }
}

// Update agent status in the UI
function updateAgentStatus(agent) {
    const agentElement = document.getElementById(`agent-${agent.name}`);
    if (agentElement) {
        agentElement.querySelector('.agent-status').textContent = agent.status;
        agentElement.querySelector('.agent-status').className = `status-badge status-${agent.status.toLowerCase()}`;
    }
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    const container = document.getElementById('notifications') || createNotificationContainer();
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Create notification container if it doesn't exist
function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'notifications';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
    `;
    document.body.appendChild(container);
    return container;
}

// Setup event listeners
function setupEventListeners() {
    // Task submission form
    const taskForm = document.getElementById('task-form');
    if (taskForm) {
        taskForm.addEventListener('submit', handleTaskSubmit);
    }
    
    // Agent control buttons
    document.querySelectorAll('.agent-control').forEach(button => {
        button.addEventListener('click', handleAgentControl);
    });
}

// Handle task submission
async function handleTaskSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const taskData = {
        type: formData.get('type'),
        description: formData.get('description'),
        requirements: JSON.parse(formData.get('requirements') || '{}')
    };
    
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('Task submitted successfully', 'success');
            event.target.reset();
            loadTasks();
        } else {
            showNotification('Failed to submit task', 'danger');
        }
    } catch (error) {
        console.error('Error submitting task:', error);
        showNotification('Error submitting task', 'danger');
    }
}

// Handle agent control actions
async function handleAgentControl(event) {
    const agentName = event.target.dataset.agent;
    const action = event.target.dataset.action;
    
    try {
        const response = await fetch(`/api/agents/${agentName}/${action}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification(`Agent ${agentName} ${action} successful`, 'success');
        } else {
            showNotification(`Failed to ${action} agent ${agentName}`, 'danger');
        }
    } catch (error) {
        console.error('Error controlling agent:', error);
        showNotification('Error controlling agent', 'danger');
    }
}

// Load tasks from server
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        renderTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// Render tasks in the UI
function renderTasks(tasks) {
    const taskList = document.getElementById('task-list');
    if (!taskList) return;
    
    taskList.innerHTML = tasks.map(task => `
        <div class="task-item" id="task-${task.id}">
            <div>
                <h4>${task.description}</h4>
                <span class="status-badge status-${task.status.toLowerCase()}">${task.status}</span>
            </div>
            <div>
                <button class="btn btn-primary" onclick="viewTask('${task.id}')">View</button>
            </div>
        </div>
    `).join('');
}

// View task details
async function viewTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const task = await response.json();
        showTaskModal(task);
    } catch (error) {
        console.error('Error loading task:', error);
        showNotification('Error loading task details', 'danger');
    }
}

// Show task modal
function showTaskModal(task) {
    // Modal implementation
    console.log('Show task modal:', task);
}

// Utility function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Export functions for use in HTML
window.showNotification = showNotification;
window.viewTask = viewTask;
window.loadTasks = loadTasks;
