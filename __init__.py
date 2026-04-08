"""Custom Calendar Events integration for Home Assistant."""

import logging
import datetime
import dataclasses
from collections.abc import Iterable
from typing import Any, Final

import voluptuous as vol

from homeassistant.components.calendar import CalendarEntity
from homeassistant.components.calendar.const import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
from homeassistant.util.json import JsonValueType

from .const import (
    DATA_COMPONENT,
    DOMAIN,
    EVENT_DURATION,
    EVENT_END_DATETIME,
    EVENT_START_DATETIME,
    LIST_EVENT_FIELDS,
    CalendarEntityFeature,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_EVENTS = "get_events"
SERVICE_DELETE_EVENT = "delete_event"
SERVICE_DELETE_EVENTS_IN_RANGE = "delete_events_in_range"

CONF_CALENDAR_ID = "calendar_id"
CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_EVENT_ID = "event_id"
CONF_RECURRENCE_ID = "recurrence_id"
CONF_RECURRENCE_RANGE = "recurrence_range"

SCAN_INTERVAL = datetime.timedelta(seconds=60)

SERVICE_DELETE_EVENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CALENDAR_ID): cv.entity_id,
        vol.Required(CONF_EVENT_ID): cv.string,
        vol.Optional(CONF_RECURRENCE_ID): vol.Any(cv.string, None),
        vol.Optional(CONF_RECURRENCE_RANGE): vol.In(["THIS", "THIS_AND_FUTURE"]),
    }
)

SERVICE_DELETE_EVENTS_IN_RANGE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CALENDAR_ID): cv.entity_id,
        vol.Required(CONF_START_DATE): cv.string,
        vol.Required(CONF_END_DATE): cv.string,
    }
)


def _has_positive_interval(
    start_key: str, end_key: str, duration_key: str
) -> Any:
    """Verify that the time span between start and end is greater than zero."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        if (duration := obj.get(duration_key)) is not None:
            if duration <= datetime.timedelta(seconds=0):
                raise vol.Invalid(f"Expected positive duration ({duration})")
            return obj

        if (start := obj.get(start_key)) and (end := obj.get(end_key)):
            if start >= end:
                raise vol.Invalid(
                    f"Expected end time to be after start time ({start}, {end})"
                )
        return obj

    return validate


def _event_dict_factory(obj: Iterable[tuple[str, Any]]) -> dict[str, str]:
    """Convert CalendarEvent dataclass items to a dictionary of attributes."""
    result: dict[str, str] = {}
    for name, value in obj:
        if isinstance(value, (datetime.datetime, datetime.date)):
            result[name] = value.isoformat()
        elif value is not None:
            result[name] = str(value)
    return result


def _list_events_dict_factory(
    obj: Iterable[tuple[str, Any]],
) -> dict[str, JsonValueType]:
    """Filter and convert CalendarEvent dataclass items to a dictionary."""
    return {
        name: value
        for name, value in _event_dict_factory(obj).items()
        if name in LIST_EVENT_FIELDS and value is not None
    }


SERVICE_GET_EVENTS_SCHEMA: Final = vol.All(
    cv.has_at_least_one_key(EVENT_END_DATETIME, EVENT_DURATION),
    cv.has_at_most_one_key(EVENT_END_DATETIME, EVENT_DURATION),
    cv.make_entity_service_schema(
        {
            vol.Optional(CONF_CALENDAR_ID): cv.entity_id,
            vol.Optional(EVENT_START_DATETIME): cv.datetime,
            vol.Optional(EVENT_END_DATETIME): cv.datetime,
            vol.Optional(EVENT_DURATION): vol.All(
                cv.time_period, cv.positive_timedelta
            ),
        }
    ),
    _has_positive_interval(EVENT_START_DATETIME, EVENT_END_DATETIME, EVENT_DURATION),
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Custom Calendar Events integration."""

    component = hass.data[DATA_COMPONENT] = EntityComponent[CalendarEntity](
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )

    def _get_calendar_entity(calendar_id: str) -> CalendarEntity:
        """Look up a calendar entity and verify it supports event deletion."""
        entity = next(
            (
                e for e in hass.data["entity_components"][CALENDAR_DOMAIN].entities
                if e.entity_id == calendar_id
            ),
            None,
        )
        if entity is None:
            raise HomeAssistantError(f"Calendar with ID {calendar_id} not found")
        if not entity.supported_features or not entity.supported_features & CalendarEntityFeature.DELETE_EVENT:
            raise HomeAssistantError("Calendar does not support deleting events")
        return entity

    async def async_delete_event_service(call: ServiceCall) -> None:
        """Delete a single event from a calendar."""
        calendar_id = call.data[CONF_CALENDAR_ID]
        event_id = call.data[CONF_EVENT_ID]
        recurrence_id = call.data.get(CONF_RECURRENCE_ID)
        recurrence_range = call.data.get(CONF_RECURRENCE_RANGE)

        calendar_entity = _get_calendar_entity(calendar_id)

        try:
            await calendar_entity.async_delete_event(
                event_id,
                recurrence_id=recurrence_id,
                recurrence_range=recurrence_range,
            )
            _LOGGER.info("Event %s deleted", event_id)
            hass.data["service_response"] = {"success": True}
        except Exception as err:
            _LOGGER.error("Failed to delete event: %s", err)
            hass.data["service_response"] = {"success": False}

    async def async_delete_events_in_range(call: ServiceCall) -> None:
        """Delete all events within a date range from a calendar."""
        calendar_id = call.data[CONF_CALENDAR_ID]
        start_date = dt_util.as_local(datetime.datetime.fromisoformat(call.data[CONF_START_DATE])).date()
        end_date = dt_util.as_local(datetime.datetime.fromisoformat(call.data[CONF_END_DATE])).date()

        calendar_entity = _get_calendar_entity(calendar_id)

        try:
            dt_start = dt_util.as_local(datetime.datetime.combine(start_date, datetime.time.min))
            dt_end = dt_util.as_local(datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min))
            events = await calendar_entity.async_get_events(hass, dt_start, dt_end)
            deleted_count = 0

            for event in events:
                event_start = event.start
                event_end = event.end

                if isinstance(event_start, datetime.datetime):
                    event_start_date = event_start.date()
                else:
                    event_start_date = event_start

                if isinstance(event_end, datetime.datetime):
                    event_end_date = event_end.date()
                    if event_end.hour == 0 and event_end.minute == 0 and event_end.second == 0:
                        event_end_date = (event_end - datetime.timedelta(days=1)).date()
                else:
                    event_end_date = event_end - datetime.timedelta(days=1)  # DTEND is exclusive

                if event_end_date < start_date or event_start_date > end_date:
                    continue  # outside the requested range

                try:
                    await calendar_entity.async_delete_event(event.uid)
                    _LOGGER.info("Event %s deleted", event.uid)
                    deleted_count += 1
                except Exception as event_err:
                    _LOGGER.warning("Failed to delete event %s: %s", event.uid, event_err)

            hass.data["service_response"] = {"deleted": deleted_count}
        except Exception as err:
            _LOGGER.error("Failed to delete events in range: %s", err)
            hass.data["service_response"] = {"success": False}

    async def async_get_events_service(service_call: ServiceCall) -> ServiceResponse:
        """Return events from a calendar within a given time window."""
        start = service_call.data.get(EVENT_START_DATETIME, dt_util.now())
        if EVENT_DURATION in service_call.data:
            end = start + service_call.data[EVENT_DURATION]
        else:
            end = service_call.data[EVENT_END_DATETIME]

        calendar_id = service_call.data[CONF_CALENDAR_ID]

        calendar = next(
            (
                e for e in hass.data["entity_components"][CALENDAR_DOMAIN].entities
                if e.entity_id == calendar_id
            ),
            None,
        )

        if calendar is None:
            raise HomeAssistantError(f"Calendar with ID {calendar_id} not found")

        events = await calendar.async_get_events(hass, dt_util.as_local(start), dt_util.as_local(end))
        _LOGGER.info("%d events found", len(events))

        return {
            "events": [
                dataclasses.asdict(event, dict_factory=_list_events_dict_factory)
                for event in events
            ]
        }

    component.async_register_entity_service(
        SERVICE_GET_EVENTS,
        SERVICE_GET_EVENTS_SCHEMA,
        async_get_events_service,
        supports_response=SupportsResponse.ONLY,
    )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_EVENT,
        async_delete_event_service,
        schema=SERVICE_DELETE_EVENT_SCHEMA,
    )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_EVENTS_IN_RANGE,
        async_delete_events_in_range,
        schema=SERVICE_DELETE_EVENTS_IN_RANGE_SCHEMA,
    )

    return True
