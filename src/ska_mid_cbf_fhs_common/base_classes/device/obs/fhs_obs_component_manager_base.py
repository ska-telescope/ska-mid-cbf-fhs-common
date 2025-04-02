from __future__ import annotations  # allow forward references in type hints

from typing import Any, Callable

from ska_control_model import ObsState, ResultCode

from ska_mid_cbf_fhs_common.base_classes.device.fhs_component_manager_base import FhsComponentManagerBase
from ska_mid_cbf_fhs_common.state_model.fhs_obs_state import FhsObsStateMachine


class FhsObsComponentManagerBase(FhsComponentManagerBase):
    def __init__(
        self: FhsObsComponentManagerBase,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.obs_state = ObsState.IDLE
        super().__init__(
            *args,
            **kwargs,
        )

    ####
    # Allowance Functions
    ####

    def is_recover_allowed(self: FhsObsComponentManagerBase) -> bool:
        self.logger.debug("Checking if Recover is allowed...")
        errorMsg = f"Device {self._device_id}  recover not allowed in ObsState {self.obs_state}; \
            must be in ObsState.IDLE or READY or ABORTED or RESETTING"
        return self.is_allowed(errorMsg, [ObsState.IDLE, ObsState.FAULT, ObsState.READY, ObsState.ABORTED])

    def is_configure_allowed(self: FhsObsComponentManagerBase) -> bool:
        self.logger.debug("Checking if Configure is allowed...")
        errorMsg = f"Device {self._device_id} Configure not allowed in ObsState {self.obs_state}; \
            must be in ObsState.IDLE or READY"

        return self.is_allowed(errorMsg, [ObsState.IDLE, ObsState.READY])

    def is_start_allowed(self: FhsObsComponentManagerBase) -> bool:
        self.logger.debug("Checking if Start is allowed...")
        errorMsg = f"Device {self._device_id} Start not allowed in ObsState {self.obs_state}; \
            must be in ObsState.IDLE or READY"

        return self.is_allowed(errorMsg, [ObsState.IDLE, ObsState.READY])

    def is_stop_allowed(self: FhsObsComponentManagerBase) -> bool:
        self.logger.debug("Checking if Stop is allowed...")
        errorMsg = f"Device {self._device_id} stop not allowed in ObsState {self.obs_state}; \
            must be in ObsState.IDLE, READY or ABORTED"

        return self.is_allowed(errorMsg, [ObsState.IDLE, ObsState.READY, ObsState.SCANNING, ObsState.ABORTED, ObsState.FAULT])

    def is_deconfigure_allowed(self: FhsObsComponentManagerBase) -> bool:
        self.logger.debug("Checking if Stop is allowed...")
        errorMsg = f"Device {self._device_id} deconfigure not allowed in ObsState {self.obs_state}; \
            must be in ObsState.READY"

        return self.is_allowed(errorMsg, [ObsState.IDLE, ObsState.READY, ObsState.ABORTED, ObsState.FAULT])

    def is_go_to_idle_allowed(self: FhsComponentManagerBase) -> bool:
        self.logger.debug("Checking if gotoidle is allowed...")
        errorMsg = f"go_to_idle not allowed in ObsState {self.obs_state}; " "must be in ObsState.READY"

        return self.is_allowed(errorMsg, [ObsState.READY, ObsState.ABORTED, ObsState.FAULT])

    def is_allowed(self: FhsComponentManagerBase, error_msg: str, obsStates: list[ObsState]) -> bool:
        result = True

        if self.obs_state not in obsStates:
            self.logger.warning(error_msg)
            result = False

        return result

    ########
    # Commands
    ########
    def go_to_idle(self: FhsComponentManagerBase) -> tuple[ResultCode, str]:
        self.logger.debug(f"Component state: {self._component_state}")

        msg = "GoToIdle called sucessfully"

        if self.obs_state != ObsState.IDLE:
            if self.is_go_to_idle_allowed():
                self._obs_state_action_callback(FhsObsStateMachine.GO_TO_IDLE)
        else:
            msg = "Already in the IDLE State"

        return ResultCode.OK, msg

    ###
    # Utility functions
    ###

    def _obs_command_with_callback(
        self: FhsComponentManagerBase,
        *args,
        command_thread: Callable[[Any], None],
        hook: str,
        **kwargs,
    ):
        """
        Wrap command thread with ObsStateModel-driving callbacks.

        :param command_thread: actual command thread to be executed
        :param hook: hook for state machine action
        """
        self._obs_command_running_callback(hook=hook, running=True)
        command_thread(*args, **kwargs)
        self._obs_command_running_callback(hook=hook, running=False)
