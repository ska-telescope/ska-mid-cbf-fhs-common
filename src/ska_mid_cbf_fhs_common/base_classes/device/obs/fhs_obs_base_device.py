from __future__ import annotations

from logging import Logger

from ska_control_model import ObsState
from ska_mid_cbf_fhs_common.base_classes.device.fhs_base_device import FhsBaseDevice
from ska_mid_cbf_fhs_common.state_model.fhs_obs_state import FhsObsStateMachine, FhsObsStateModel
from ska_tango_base import SKAObsDevice
from tango.server import command, DebugIt  # Ensure command and DebugIt are imported
from tango import DevVarLongStringArray  # Import the correct type

class FhsObsBaseDevice(SKAObsDevice, FhsBaseDevice):

    def init_device(self: FhsBaseDevice) -> None:
        super().init_device()
        self._update_obs_state(obs_state=ObsState.IDLE)

    ##############
    # Commands
    ##############
    @command(dtype_out="DevVarLongStringArray")
    @DebugIt()
    def GoToIdle(self: FhsBaseDevice) -> DevVarLongStringArray:
        command_handler = self.get_command_object(command_name="GoToIdle")
        result_code_message, command_id = command_handler()
        return [[result_code_message], [command_id]]
    
    ###############
    # Functions
    ###############
    def _init_state_model(self: FhsBaseDevice) -> None:
        """Set up the state model for the device."""
        super()._init_state_model()

        # supplying the reduced observing state machine defined above
        self.obs_state_model = FhsObsStateModel(
            logger=self.logger,
            callback=self._update_obs_state,
            state_machine_factory=FhsObsStateMachine,
        )

    def reset_obs_state(self: FhsBaseDevice):
        if self._obs_state in [ObsState.FAULT, ObsState.ABORTED]:
            self.obs_state_model.perform_action(FhsObsStateMachine.GO_TO_IDLE)

    def _obs_command_running(self: FhsBaseDevice, hook: str, running: bool) -> None:
        """
        Callback provided to component manager to drive the obs state model into
        transitioning states during the relevant command's submitted thread.

        :param hook: the observing command-specific hook
        :param running: True when thread begins, False when thread completes
        """
        action = "invoked" if running else "completed"
        self.logger.info(f"Changing ObsState from running command, calling: {hook}_{action} ")
        self.obs_state_model.perform_action(f"{hook}_{action}")

    def _obs_state_action(self: FhsBaseDevice, action: str) -> None:
        self.obs_state_model.perform_action(action)

    def _update_obs_state(self: FhsBaseDevice, obs_state: ObsState) -> None:
        """
        Perform Tango operations in response to a change in obsState within the state machine.

        This helper method is passed to the observation state model as a
        callback, so that the model can trigger actions in the Tango
        device.

        Overridden here to supply new ObsState value to component manager property

        :param obs_state: the new obs_state value
        """
        self.logger.debug(f"ObsState updating to {ObsState(obs_state).name}")

        super()._update_obs_state(obs_state=obs_state)

        # set the obstate in the component_manager
        if hasattr(self, "component_manager"):
            self.component_manager.obs_state = obs_state