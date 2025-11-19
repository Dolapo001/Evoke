// Register service worker and enable notifications
class NotificationManager {
    constructor() {
        this.swRegistration = null;
        this.isSubscribed = false;
        this.init();
    }

    async init() {
        if ('serviceWorker' in navigator && 'PushManager' in window) {
            try {
                this.swRegistration = await navigator.serviceWorker.register('/serviceworker.js');
                this.initializeUI();
            } catch (error) {
                console.error('Service Worker Error', error);
            }
        } else {
            console.warn('Push messaging is not supported');
        }
    }

    initializeUI() {
        // Check current subscription status
        this.swRegistration.pushManager.getSubscription()
            .then(subscription => {
                this.isSubscribed = !(subscription === null);
                this.updateSubscriptionOnServer(subscription);
                
                if (this.isSubscribed) {
                    console.log('User IS subscribed.');
                } else {
                    console.log('User is NOT subscribed.');
                    this.subscribeUser();
                }
            });
    }

    async subscribeUser() {
        const applicationServerKey = this.urlB64ToUint8Array('{{ VAPID_PUBLIC_KEY }}');
        
        try {
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });
            
            console.log('User is subscribed:', subscription);
            this.isSubscribed = true;
            this.updateSubscriptionOnServer(subscription);
        } catch (err) {
            console.log('Failed to subscribe the user: ', err);
        }
    }

    async updateSubscriptionOnServer(subscription) {
        if (subscription) {
            const response = await fetch('/notifications/save-subscription/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ subscription })
            });
            
            const data = await response.json();
            console.log('Subscription saved:', data);
        }
    }

    urlB64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // Request notification permission
    async requestPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }
        return false;
    }

    // Show local notification
    showLocalNotification(title, message, icon = '/static/images/logo.png') {
        if ('Notification' in window && Notification.permission === 'granted') {
            const options = {
                body: message,
                icon: icon,
                badge: '/static/images/badge.png',
                tag: 'evoke-notification',
                renotify: true,
                actions: [
                    {
                        action: 'view',
                        title: 'View'
                    },
                    {
                        action: 'close',
                        title: 'Close'
                    }
                ]
            };
            
            const notification = new Notification(title, options);
            
            notification.onclick = function() {
                window.focus();
                notification.close();
            };
        }
    }
}

// Initialize notification manager when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
});

// Utility function to get CSRF token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}