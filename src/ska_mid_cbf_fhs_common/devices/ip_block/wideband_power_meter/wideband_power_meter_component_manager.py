from __future__ import annotations  # allow forward references in type hints

from dataclasses import dataclass
from typing import Any

import numpy as np
from dataclasses_json import dataclass_json
from marshmallow import ValidationError
from ska_control_model import CommunicationStatus, ResultCode

from ska_mid_cbf_fhs_common.base_classes.device.low_level.fhs_low_level_component_manager_base import (
    FhsLowLevelComponentManagerBase,
)
from ska_mid_cbf_fhs_common.devices.ip_block.wideband_power_meter.wideband_power_meter_simulator import (
    WidebandPowerMeterSimulator,
)


@dataclass_json
@dataclass
class WidebandPowerMeterConfig:
    averaging_time: float  # Averaging interval in seconds
    sample_rate: np.uint64  # Sample rate in sampes per second
    flagging: np.uint8  # Handling for flagged data, 0 - ignore, 1 - use, 2 - saturate and use


##
# status class that will be populated by the APIs and returned to provide the status of Wideband Power Meter
##
@dataclass
class WidebandPowerMeterStatus:
    timestamp: float  # Timestamp in seconds of the last sample in the averaging interval
    avg_power_polX: float  # Average signal power
    avg_power_polY: float  # Average signal power
    avg_power_polX_noise_diode_on: float  # Average signal power
    avg_power_polY_noise_diode_on: float  # Average signal power
    avg_power_polX_noise_diode_off: float  # Average signal power
    abg_power_polY_noise_diode_off: float  # Average signal power
    flag: bool  # Flagged data detected during averaging interval
    # Overflow detected during averaging interval: bit 0 nd on pol X, bit 1 nd on pol Y, bit 2 nd off pol X, bit 3 nd off pol Y
    overflow: np.uint8


class WidebandPowerMeterComponentManager(FhsLowLevelComponentManagerBase):
    def __init__(
        self: WidebandPowerMeterComponentManager,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            simulator_api=WidebandPowerMeterSimulator,
            **kwargs,
        )

    # ------------------
    # Public Commands
    # ------------------

    def configure(self: WidebandPowerMeterComponentManager, argin: str) -> tuple[ResultCode, str]:
        try:
            self.logger.info("WPM Configuring..")

            wpmJsonConfig: WidebandPowerMeterConfig = WidebandPowerMeterConfig.schema().loads(argin)

            self.logger.info(f"CONFIG JSON CONFIG: {wpmJsonConfig.to_json()}")

            result: tuple[ResultCode, str] = (
                ResultCode.OK,
                f"{self._device_id} configured successfully",
            )

            self.logger.info(f"WPM JSON CONFIG: {wpmJsonConfig.to_json()}")

            result = super().configure(wpmJsonConfig.to_dict())

            if result[0] != ResultCode.OK:
                self.logger.error(f"Configuring {self._device_id} failed. {result[1]}")

        except ValidationError as vex:
            errorMsg = "Validation error: argin doesn't match the required schema"
            self.logger.error(f"{errorMsg}: {vex}")
            result = ResultCode.FAILED, errorMsg
        except Exception as ex:
            errorMsg = f"Unable to configure {self._device_id}"
            self.logger.error(f"{errorMsg}: {ex!r}")
            result = ResultCode.FAILED, errorMsg

        return result

    # TODO Determine what needs to be communicated with here
    def start_communicating(self: WidebandPowerMeterComponentManager) -> None:
        """Establish communication with the component, then start monitoring."""
        if self._communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Already communicating.")
            return

        super().start_communicating()
