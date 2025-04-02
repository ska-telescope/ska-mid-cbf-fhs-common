from __future__ import annotations

from logging import Logger
from typing import TypeVar, cast

from ska_control_model import CommunicationStatus, HealthState, ResultCode
from ska_tango_base import SKABaseDevice
from ska_tango_base.base.base_device import DevVarLongStringArrayType
from ska_tango_base.commands import ArgumentValidator, FastCommand, SubmittedSlowCommand, _BaseCommand
from tango import DebugIt, DevState
from tango.server import attribute, command, device_property

from ska_mid_cbf_fhs_common.base_classes.device.fhs_component_manager_base import FhsComponentManagerBase

__all__ = ["FhsBaseDevice", "FhsFastCommand", "main"]

CompManager = TypeVar("CompManager", bound=FhsComponentManagerBase)


# -----------------------------------------------------
# FhsFastCommand class
#
# -----------------------------------------------------
class FhsFastCommand(FastCommand):
    def __init__(
        self: _BaseCommand,
        component_manager: CompManager,
        logger: Logger | None = None,
        validator: ArgumentValidator | None = None,
    ) -> None:
        super().__init__(logger, validator)
        self._component_manager = component_manager


# -----------------------------------------------------
# FhsBaseDevice class
#
# -----------------------------------------------------
class FhsBaseDevice(SKABaseDevice):
    # -----------------
    # Device Properties
    # -----------------
    device_id = device_property(dtype="int")
    device_version_num = device_property(dtype="str")
    device_gitlab_hash = device_property(dtype="str")
    simulation_mode = device_property(dtype="int")
    emulation_mode = device_property(dtype="int")

    # -----------------
    # Device Attributes
    # -----------------
    @attribute(dtype=CommunicationStatus)
    def communicationState(self: FhsBaseDevice) -> CommunicationStatus:
        return self.component_manager.communication_state

    ###############
    # Functions
    ###############
    def init_command_objects(self: FhsBaseDevice, commandsAndMethods: list[tuple] | None = None) -> None:
        """Set up the command objects."""
        super().init_command_objects()

        if commandsAndMethods:
            for command_name, method_name in commandsAndMethods:
                self.register_command_object(
                    command_name,
                    SubmittedSlowCommand(
                        command_name=command_name,
                        command_tracker=self._command_tracker,
                        component_manager=self.component_manager,
                        method_name=method_name,
                        logger=self.logger,
                    ),
                )

    def init_fast_command_objects(self: FhsBaseDevice, commandsAndClasses: list[tuple]) -> None:
        for command_name, fast_command in commandsAndClasses:
            self.register_command_object(
                command_name,
                fast_command(
                    component_manager=self.component_manager,
                    logger=self.logger,
                ),
            )

    def _communication_state_changed(self: FhsBaseDevice, communication_state: CommunicationStatus) -> None:
        super()._communication_state_changed(communication_state=communication_state)
        self.push_change_event("communicationState", communication_state)

    def init_device(self: FhsBaseDevice) -> None:
        super().init_device()
        self.set_state(DevState.ON)
        self.set_status("ON")
        self.set_change_event("communicationState", True)
        self._update_health_state(HealthState.OK)

    def get_dev_state(self: FhsBaseDevice) -> DevState:
        return self.dev_state()

    # ----------------------
    # Unimplemented Commands
    # ----------------------

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def On(self: FhsBaseDevice) -> DevVarLongStringArrayType:
        """
        Turn device on.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["On command rejected, as it is unimplemented for this device."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Off(self: FhsBaseDevice) -> DevVarLongStringArrayType:
        """
        Turn device off.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["Off command rejected, as it is unimplemented for this device."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Standby(self: FhsBaseDevice) -> DevVarLongStringArrayType:
        """
        Put the device into standby mode; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["Standby command rejected; Mid.CBF does not currently implement standby state."],
        )

    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def Reset(self: FhsBaseDevice) -> DevVarLongStringArrayType:
        """
        Reset the device; currently unimplemented in Mid.CBF

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        return (
            [ResultCode.REJECTED],
            ["Reset command rejected, as it is unimplemented for this device."],
        )

    class GoToIdleCommand(FhsFastCommand):
        def do(self) -> tuple[ResultCode, str]:
            return self._component_manager.go_to_idle()


# ----------
# Run server
# ----------
def main(*args: str, **kwargs: str) -> int:
    """
    Entry point for module.

    :param args: positional arguments
    :param kwargs: named arguments

    :return: exit code
    """
    return cast(int, FhsBaseDevice.run_server(args=args or None, **kwargs))


if __name__ == "__main__":
    main()
