import enum
import logging
from typing import Any, Dict, Optional

import click

from miio.airfilter_util import FilterTypeUtil
from miio.click_common import EnumType, command, format_output
from miio.exceptions import DeviceException
from miio.miot_device import DeviceStatus, MiotDevice

# https://miot-spec.org/miot-spec-v2/instance?type=urn:miot-spec-v2:device:air-purifier:0000A007:zhimi-za1:1
_MODEL_AIRPURIFIER_ZA1 = {
    # Air Purifier
    "power": {"siid": 2, "piid": 1},
    "mode": {"siid": 2, "piid": 5},
    # Environment
    "tvoc": {"siid": 3, "piid": 1},
    "pm25": {"siid": 3, "piid": 6},
    "humidity": {"siid": 3, "piid": 7},
    "temperature": {"siid": 3, "piid": 8},
    # Filter
    "filter_life_remaining": {"siid": 4, "piid": 3},
    "filter_hours_used": {"siid": 4, "piid": 5},
    # Alarm
    "buzzer": {"siid": 5, "piid": 1},
    # Screen
    "led_brightness": {"siid": 6, "piid": 1},
    # Physical Control Locked
    "child_lock": {"siid": 7, "piid": 1},
    # Motor Speed (siid=10)
    "favorite_level": {"siid": 10, "piid": 10},
    "motor_speed": {"siid": 10, "piid": 11},
    # Use time (siid=12)
    "use_time": {"siid": 12, "piid": 1},
    # AQI (siid=13)
    "purify_volume": {"siid": 13, "piid": 1},
    "average_aqi": {"siid": 13, "piid": 2},
    # RFID (siid=14)
    "filter_rfid_tag": {"siid": 14, "piid": 1},
    "filter_rfid_product_id": {"siid": 14, "piid": 3},
    # custom-service
    "gesture_status": {"siid": 15, "piid": 13}
}


class AirPurifierMiotException(DeviceException):
    pass


class OperationMode(enum.Enum):
    Auto = 0
    Silent = 1
    Favorite = 2
    Fan = 3


class LedBrightness(enum.Enum):
    Bright = 0
    Dim = 1
    Off = 2


class BasicAirPurifierMiotStatus(DeviceStatus):
    """Container for status reports from the air purifier."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self.filter_type_util = FilterTypeUtil()
        self.data = data

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.data["power"]

    @property
    def power(self) -> str:
        """Power state."""
        return "on" if self.is_on else "off"

    @property
    def tvoc(self) -> int:
        """Air quality index."""
        return self.data["tvoc"]

    @property
    def mode(self) -> OperationMode:
        """Current operation mode."""
        return OperationMode(self.data["mode"])

    @property
    def buzzer(self) -> Optional[bool]:
        """Return True if buzzer is on."""
        if self.data["buzzer"] is not None:
            return self.data["buzzer"]

        return None

    @property
    def child_lock(self) -> bool:
        """Return True if child lock is on."""
        return self.data["child_lock"]

    @property
    def filter_life_remaining(self) -> int:
        """Time until the filter should be changed."""
        return self.data["filter_life_remaining"]

    @property
    def filter_hours_used(self) -> int:
        """How long the filter has been in use."""
        return self.data["filter_hours_used"]

    @property
    def motor_speed(self) -> int:
        """Speed of the motor."""
        return self.data["motor_speed"]

    @property
    def favorite_rpm(self) -> Optional[int]:
        """Return favorite rpm level."""
        return self.data.get("favorite_rpm")

class AirPurifierZA1Status(BasicAirPurifierMiotStatus):
    """
    Container for status reports from the  Mi Air Purifier 3C (zhimi.airpurifier.mb4).

    {
        'power': True,
        'mode': 1,
        'tvoc': 2,
        'filter_life_remaining': 97,
        'filter_hours_used': 100,
        'buzzer': True,
        'led_brightness_level': 8,
        'child_lock': False,
        'motor_speed': 392,
        'favorite_rpm': 500
    }

    Response (MIoT format)

    [
        {'did': 'power', 'siid': 2, 'piid': 1, 'code': 0, 'value': True},
        {'did': 'mode', 'siid': 2, 'piid': 4, 'code': 0, 'value': 1},
        {'did': 'tvoc', 'siid': 3, 'piid': 4, 'code': 0, 'value': 3},
        {'did': 'filter_life_remaining', 'siid': 4, 'piid': 1, 'code': 0, 'value': 97},
        {'did': 'filter_hours_used', 'siid': 4, 'piid': 3, 'code': 0, 'value': 100},
        {'did': 'buzzer', 'siid': 6, 'piid': 1, 'code': 0, 'value': True},
        {'did': 'led_brightness_level', 'siid': 7, 'piid': 2, 'code': 0, 'value': 8},
        {'did': 'child_lock', 'siid': 8, 'piid': 1, 'code': 0, 'value': False},
        {'did': 'motor_speed', 'siid': 9, 'piid': 1, 'code': 0, 'value': 388},
        {'did': 'favorite_rpm', 'siid': 9, 'piid': 3, 'code': 0, 'value': 500}
    ]

    """
    @property
    def average_aqi(self) -> int:
        """Average of the air quality index."""
        return self.data["average_aqi"]

    @property
    def humidity(self) -> int:
        """Current humidity."""
        return self.data["humidity"]

    @property
    def temperature(self) -> Optional[float]:
        """Current temperature, if available."""
        if self.data["temperature"] is not None:
            return round(self.data["temperature"], 1)

        return None

    # @property
    # def fan_level(self) -> int:
    #     """Current fan level."""
    #     return self.data["fan_level"]

    # @property
    # def led(self) -> bool:
    #     """Return True if LED is on."""
    #     return self.data["led"]

    @property
    def led_brightness(self) -> Optional[LedBrightness]:
        """Brightness of the LED."""
        if self.data["led_brightness"] is not None:
            try:
                return LedBrightness(self.data["led_brightness"])
            except ValueError:
                return None

        return None

    # @property
    # def buzzer_volume(self) -> Optional[int]:
    #     """Return buzzer volume."""
    #     if self.data["buzzer_volume"] is not None:
    #         return self.data["buzzer_volume"]

    #     return None

    @property
    def favorite_level(self) -> int:
        """Return favorite level, which is used if the mode is ``favorite``."""
        # Favorite level used when the mode is `favorite`.
        return self.data["favorite_level"]

    @property
    def use_time(self) -> int:
        """How long the device has been active in seconds."""
        return self.data["use_time"]

    @property
    def purify_volume(self) -> int:
        """The volume of purified air in cubic meter."""
        return self.data["purify_volume"]

    @property
    def filter_rfid_product_id(self) -> Optional[str]:
        """RFID product ID of installed filter."""
        return self.data["filter_rfid_product_id"]

    @property
    def filter_rfid_tag(self) -> Optional[str]:
        """RFID tag ID of installed filter."""
        return self.data["filter_rfid_tag"]

    # @property
    # def filter_type(self) -> Optional[FilterType]:
    #     """Type of installed filter."""
    #     return self.filter_type_util.determine_filter_type(
    #         self.filter_rfid_tag, self.filter_rfid_product_id
    #     )

    @property
    def pm25(self) -> int:
        """Return pm 2.5 density level."""
        return self.data["pm25"]
    @property
    def gesture_status(self) -> bool:
        """Return gesture control status."""
        return self.data["gesture_status"]

class BasicAirPurifierMiot(MiotDevice):
    """Main class representing the air purifier which uses MIoT protocol."""

    @command(default_output=format_output("Powering on"))
    def on(self):
        """Power on."""
        return self.set_property("power", True)

    @command(default_output=format_output("Powering off"))
    def off(self):
        """Power off."""
        return self.set_property("power", False)

    @command(
        click.argument("rpm", type=int),
        default_output=format_output("Setting favorite motor speed '{rpm}' rpm"),
    )
    def set_favorite_rpm(self, rpm: int):
        """Set favorite motor speed."""
        # Note: documentation says the maximum is 2300, however, the purifier may return an error for rpm over 2200.
        if rpm < 300 or rpm > 2300 or rpm % 10 != 0:
            raise AirPurifierMiotException(
                "Invalid favorite motor speed: %s. Must be between 300 and 2300 and divisible by 10"
                % rpm
            )
        return self.set_property("favorite_rpm", rpm)

    @command(
        click.argument("mode", type=EnumType(OperationMode)),
        default_output=format_output("Setting mode to '{mode.value}'"),
    )
    def set_mode(self, mode: OperationMode):
        """Set mode."""
        return self.set_property("mode", mode.value)

    @command(
        click.argument("buzzer", type=bool),
        default_output=format_output(
            lambda buzzer: "Turning on buzzer" if buzzer else "Turning off buzzer"
        ),
    )
    def set_buzzer(self, buzzer: bool):
        """Set buzzer on/off."""
        return self.set_property("buzzer", buzzer)

    @command(
        click.argument("lock", type=bool),
        default_output=format_output(
            lambda lock: "Turning on child lock" if lock else "Turning off child lock"
        ),
    )
    def set_child_lock(self, lock: bool):
        """Set child lock on/off."""
        return self.set_property("child_lock", lock)

class AirPurifierZA1(BasicAirPurifierMiot):
    """Main class representing the air purifier which uses MIoT protocol."""

    mapping = _MODEL_AIRPURIFIER_ZA1

    @command(
        default_output=format_output(
            "",
            "Power: {result.power}\n"
            "TVOC: {result.tvoc} μg/m³\n"
            "PM2.5: {result.pm25} ppm\n"
            "Mode: {result.mode}\n"
            "LED brightness level: {result.led_brightness_level}\n"
            "Buzzer: {result.buzzer}\n"
            "Child lock: {result.child_lock}\n"
            "Filter life remaining: {result.filter_life_remaining} %\n"
            "Filter hours used: {result.filter_hours_used}\n"
            "Motor speed: {result.motor_speed} rpm\n"
            "Favorite RPM: {result.favorite_rpm} rpm\n",
        )
    )
    def status(self) -> AirPurifierZA1Status:
        """Retrieve properties."""
        return AirPurifierZA1Status(
            {
                prop["did"]: prop["value"] if prop["code"] == 0 else None
                for prop in self.get_properties_for_mapping()
            }
        )

    @command(
        click.argument("gesture", type=bool),
        default_output=format_output(
            lambda buzzer: "Turning on gesture control" if gesture else "Turning off gesture control"
        ),
    )
    def set_gesture(self, gesture: bool):
        """Set gesture control on/off."""
        return self.set_property("gesture", gesture)

    @command(
        click.argument("level", type=int),
        default_output=format_output("Setting favorite level to {level}"),
    )
    def set_favorite_level(self, level: int):
        """Set the favorite level used when the mode is `favorite`.
        Needs to be between 0 and 14.
        """
        if level < 0 or level > 14:
            raise AirPurifierMiotException("Invalid favorite level: %s" % level)
        return self.set_property("favorite_level", level)

    @command(
        click.argument("brightness", type=EnumType(LedBrightness)),
        default_output=format_output("Setting LED brightness to {brightness}"),
    )
    def set_led_brightness(self, brightness: LedBrightness):
        """Set led brightness."""
        return self.set_property("led_brightness", brightness.value)

