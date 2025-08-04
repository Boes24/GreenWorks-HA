"""Constants for the Greenworks integration."""

from enum import Enum, IntFlag

DOMAIN = "greenworks"
CONF_MOWER_NAME = "mower_name"

SERVICE_DOCK = "dock"
SERVICE_PAUSE = "pause"
SERVICE_START_MOWING = "start_mowing"


class LawnMowerActivity(str, Enum):
    """Possible states of the lawn mower."""
    IDLE = "idle"
    MOWING = "mowing"
    DOCKED = "docked"
    PAUSED = "paused"
    ERROR = "error"


class LawnMowerEntityFeature(IntFlag):
    """Supported features of a lawn mower."""

    START_MOWING = 1
    PAUSE = 2
    DOCK = 4
