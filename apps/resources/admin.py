from fastadmin import TortoiseModelAdmin, register
from .models import Event
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import BaseEvent, Event, Tournament
from tortoise import Tortoise

from fastadmin import TortoiseInlineModelAdmin, TortoiseModelAdmin, WidgetType, action, display
from fastadmin import fastapi_app as admin_app
from fastadmin import register


class EventInlineModelAdmin(TortoiseInlineModelAdmin):
    model = Event


@register(Tournament)
class TournamentModelAdmin(TortoiseModelAdmin):
    list_display = ("id", "name")
    inlines = (EventInlineModelAdmin,)


@register(BaseEvent)
class BaseEventModelAdmin(TortoiseModelAdmin):
    pass


@register(Event)
class EventModelAdmin(TortoiseModelAdmin):
    actions = ("make_is_active", "make_is_not_active")
    list_display = ("id", "name_with_price", "rating", "event_type", "is_active", "started")

    @action(description="Make event active")
    async def make_is_active(self, ids):
        await self.model_cls.filter(id__in=ids).update(is_active=True)

    @action
    async def make_is_not_active(self, ids):
        await self.model_cls.filter(id__in=ids).update(is_active=False)

    @display
    async def started(self, obj):
        return bool(obj.start_time)

    @display()
    async def name_with_price(self, obj):
        return f"{obj.name} - {obj.price}"

