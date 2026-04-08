# Custom Calendar Events

A custom integration for [Home Assistant](https://www.home-assistant.io/) that extends the built-in calendar component with additional event management services.

## Features

- **Get events** - query events from any calendar within a specified time window
- **Delete a single event** - remove an event by ID, with support for recurring events
- **Delete events in a date range** - bulk-delete all events within a given period

## Installation

### Manual Installation

1. Download this repository as a ZIP file (click **Code → Download ZIP** at the top of this page).
2. Extract the ZIP and copy the `custom_calendar_events` folder into your Home Assistant
   `config/custom_components/` directory. The result should look like this:
   ```
   config/
   └── custom_components/
       └── custom_calendar_events/
           ├── __init__.py
           ├── manifest.json
           ├── const.py
           ├── services.yaml
           └── icons.json
   ```
3. Add the following line to your `configuration.yaml`:
   ```yaml
   custom_calendar_events:
   ```
4. Restart Home Assistant.

## Services

### `custom_calendar_events.get_events`

Retrieves events from a calendar within a time window.

| Field | Required | Description |
|---|---|---|
| `calendar_id` | Yes | Entity ID of the target calendar |
| `start_date_time` | No | Start of the query window (defaults to now) |
| `end_date_time` | No | End of the query window |
| `duration` | No | Duration of the query window (alternative to `end_date_time`) |

Either `end_date_time` or `duration` must be provided, but not both.

---

### `custom_calendar_events.delete_event`

Deletes a single event from a calendar.

| Field | Required | Description |
|---|---|---|
| `calendar_id` | Yes | Entity ID of the target calendar |
| `event_id` | Yes | UID of the event to delete |
| `recurrence_id` | No | Identifies the specific occurrence of a recurring event |
| `recurrence_range` | No | `THIS` or `THIS_AND_FUTURE` |

> Admin access required.

---

### `custom_calendar_events.delete_events_in_range`

Deletes all events within a date range.

| Field | Required | Description |
|---|---|---|
| `calendar_id` | Yes | Entity ID of the target calendar |
| `start_date` | Yes | Start of the range |
| `end_date` | Yes | End of the range |

Returns the number of successfully deleted events.

> Admin access required.

## Requirements

- Home Assistant with the `calendar` component enabled
- The target calendar must support the `DELETE_EVENT` feature

## Credits

Created by [PKasta](https://github.com/PKasta)

Inspired by GitHub contribution graph.

## License

MIT License - see [LICENSE](LICENSE) file for details
