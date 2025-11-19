import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from .models import Notification
from apps.events.models import House


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            self.room_group_name = f"user_{self.user.id}"

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'notification_message',
                'message': message
            }
        )

    async def notification_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))


class LeaderboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "leaderboard",
            self.channel_name
        )
        await self.accept()

        # Send initial leaderboard data
        leaderboard_data = await self.get_leaderboard_data()
        await self.send(text_data=json.dumps({
            'type': 'leaderboard_update',
            'data': leaderboard_data
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "leaderboard",
            self.channel_name
        )

    @database_sync_to_async
    def get_leaderboard_data(self):
        houses = House.objects.annotate(
            total_points=Sum('score__points')
        ).order_by('-total_points')

        return [
            {
                'id': house.id,
                'name': house.name,
                'points': house.total_points or 0,
                'crest': house.crest.url if house.crest else ''
            }
            for house in houses
        ]

    async def leaderboard_update(self, event):
        await self.send(text_data=json.dumps(event))