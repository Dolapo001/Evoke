class RealTimeManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupPolling();
    }

    connectWebSocket() {
        if (typeof WebSocket === 'undefined') {
            console.log('WebSockets not supported, falling back to polling');
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/leaderboard/`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

            console.log(`Attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        }
    }

    setupPolling() {
        // Fallback polling for leaderboard updates
        setInterval(() => {
            this.pollLeaderboard();
        }, 30000); // Poll every 30 seconds

        // Poll for new notifications
        setInterval(() => {
            this.pollNotifications();
        }, 60000); // Poll every minute
    }

    async pollLeaderboard() {
        try {
            const response = await fetch('/api/leaderboard/');
            const data = await response.json();
            this.updateLeaderboard(data);
        } catch (error) {
            console.error('Error polling leaderboard:', error);
        }
    }

    async pollNotifications() {
        try {
            const response = await fetch('/notifications/user-notifications/');
            const data = await response.json();
            this.updateNotificationBadge(data.unread_count);
        } catch (error) {
            console.error('Error polling notifications:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'leaderboard_update':
                this.updateLeaderboard(data.data);
                break;
            case 'notification':
                this.showNewNotification(data.message);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateLeaderboard(leaderboardData) {
        // Update leaderboard UI
        const leaderboardElement = document.getElementById('leaderboard');
        if (leaderboardElement) {
            leaderboardElement.innerHTML = leaderboardData.map((house, index) => `
                <div class="flex items-center justify-between p-4 border-b border-red-800/30">
                    <div class="flex items-center space-x-4">
                        <span class="text-2xl font-bold ${index < 3 ? 'text-yellow-400' : 'text-gray-300'}">
                            ${index + 1}
                        </span>
                        <img src="${house.crest}" alt="${house.name}" class="w-10 h-10 object-contain">
                        <div>
                            <h3 class="font-semibold">${house.name}</h3>
                            <p class="text-sm text-gray-400">${house.points} points</p>
                        </div>
                    </div>
                    ${index < 3 ? '<span class="text-2xl">🏆</span>' : ''}
                </div>
            `).join('');
        }
    }

    updateNotificationBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.classList.toggle('hidden', count === 0);
        }
    }

    showNewNotification(message) {
        if (window.notificationManager) {
            window.notificationManager.showLocalNotification('Evoke Update', message);
        }

        // Show in-app notification toast
        this.showToast(message);
    }

    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed top-4 right-4 bg-black/80 text-white p-4 rounded-lg border border-accent shadow-lg z-50 max-w-sm';
        toast.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="w-3 h-3 bg-accent rounded-full animate-pulse"></div>
                <p>${message}</p>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Initialize real-time features
document.addEventListener('DOMContentLoaded', function() {
    window.realTimeManager = new RealTimeManager();
});