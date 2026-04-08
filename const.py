"""Constants for the Custom Calendar Events integration."""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING

from homeassistant.util.hass_dict import HassKey

if TYPE_CHECKING:
    from homeassistant.helpers.entity_component import EntityComponent
    from homeassistant.components.calendar import CalendarEntity

DOMAIN = "custom_calendar_events"
DATA_COMPONENT: HassKey[EntityComponent[CalendarEntity]] = HassKey(DOMAIN)


class CalendarEntityFeature(IntFlag):
    """Supported features of the calendar entity."""

    CREATE_EVENT = 1
    DELETE_EVENT = 2
    UPDATE_EVENT = 4


# rfc5545 fields
EVENT_UID = "uid"
EVENT_SUMMARY = "summary"
EVENT_DESCRIPTION = "description"
EVENT_LOCATION = "location"
EVENT_RECURRENCE_ID = "recurrence_id"
EVENT_RECURRENCE_RANGE = "recurrence_range"

# Service call fields
EVENT_START_DATETIME = "start_date_time"
EVENT_END_DATETIME = "end_date_time"
EVENT_DURATION = "duration"

# Fields returned by the get_events service
LIST_EVENT_FIELDS = {
    "start",
    "end",
    EVENT_SUMMARY,
    EVENT_DESCRIPTION,
    EVENT_LOCATION,
    EVENT_UID,
    EVENT_RECURRENCE_ID,
    EVENT_RECURRENCE_RANGE,
}
