from __future__ import annotations  # allow forward references in type hints

import os
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, SimulationMode, TaskStatus

from ska_mid_cbf_fhs_common.base_classes.api.fhs_base_api_interface import FhsBaseApiInterface
from ska_mid_cbf_fhs_common.base_classes.device.fhs_component_manager_base import FhsComponentManagerBase
from ska_mid_cbf_fhs_common.base_classes.device.low_level.fhs_low_level_device_base import FhsLowLevelDeviceBase
from ska_mid_cbf_fhs_common.services.api.emulator_api import EmulatorApi
from ska_mid_cbf_fhs_common.services.api.firmware_api import FirmwareApi


class FhsLowLevelComponentManagerBase(FhsComponentManagerBase):
    def __init__(
        self: FhsLowLevelComponentManagerBase,
        *args: Any,
        device: FhsLowLevelDeviceBase,
        simulator_api: FhsBaseApiInterface,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            **kwargs,
        )

        self._device = device
        self._device_id = device.device_id
        self._simulation_mode = device.simulation_mode
        self._emulation_mode = device.emulation_mode

        self.logger.info(
            f"Device Api starting for simulation_mode: {device.simulation_mode}, emulation_mode: {device.emulation_mode}"
        )
        bitstream_path = os.path.join(device.bitstream_path, device.bitstream_id, device.bitstream_version)

        self._api: FhsBaseApiInterface
        if self._simulation_mode == SimulationMode.TRUE and simulator_api is not None:
            self._api = simulator_api(self._device_id, self.logger)
        elif self._simulation_mode == SimulationMode.FALSE and self._emulation_mode and device.emulator_ip_block_id is not None:
            self._api = EmulatorApi(
                bitstream_path, device.emulator_ip_block_id, device.emulator_id, device.emulator_base_url, self.logger
            )
        else:
            self._api = FirmwareApi(bitstream_path, device.firmware_ip_block_id, self.logger)

    #####
    # Command Functions
    #####

    def test_cmd(self: FhsLowLevelComponentManagerBase, task_callback: Optional[Callable] = None) -> tuple[TaskStatus, str]:
        return [TaskStatus.COMPLETED, "Test Complete"]

    def recover(self: FhsLowLevelComponentManagerBase) -> tuple[ResultCode, str]:
        try:
            return self._api.recover()
        except Exception as ex:
            return ResultCode.FAILED, f"Recover command failed. ex={ex!r}"

    def configure(self: FhsLowLevelComponentManagerBase, argin: dict) -> tuple[ResultCode, str]:
        try:
            return self._configure(argin)
        except Exception as ex:
            return ResultCode.FAILED, f"Configure command failed. ex={ex!r}"

    def deconfigure(self: FhsLowLevelComponentManagerBase, argin: dict = None) -> tuple[ResultCode, str]:
        try:
            return self._configure(argin, True)
        except Exception as ex:
            return ResultCode.FAILED, f"Deconfigure command failed. ex={ex!r}"

    def start(self: FhsLowLevelComponentManagerBase, task_callback: Optional[Callable] = None) -> tuple[TaskStatus, str]:
        self.logger.debug(f"Component state: {self.communication_state}")
        return self.submit_task(
            func=self._start,
            task_callback=task_callback,
        )

    def stop(
        self: FhsLowLevelComponentManagerBase,
        task_callback: Optional[Callable] = tuple[TaskStatus, str],
    ) -> tuple[TaskStatus, str]:
        self.logger.debug(f"Component state: {self.communication_state}")
        return self.submit_task(
            func=self._stop,
            task_callback=task_callback,
        )

    def status(
        self: FhsLowLevelComponentManagerBase,
        clear: bool = False,
    ) -> tuple[ResultCode, dict]:
        try:
            return self._api.status(clear)
        except Exception as ex:
            return ResultCode.FAILED, f"Status command FAILED. ex={ex!r}"

    # ------------------------
    #  Private Fast Commands
    # ------------------------

    def _configure(
        self: FhsLowLevelComponentManagerBase,
        argin: dict = None,
        deconfigure: bool = False,
    ) -> tuple[ResultCode, str]:
        try:
            mode = "Configure" if not deconfigure else "Deconfigure"
            self.logger.info(f"Running {mode} command")

            if not deconfigure:
                if argin is not None:
                    return self._api.configure(argin)
                else:
                    return ResultCode.REJECTED, f"No Configuration given for {self._device_id}"
            else:
                return self._api.deconfigure(argin)

        except Exception as ex:
            return ResultCode.FAILED, f"{mode} command FAILED. ex={ex!r}"

    # -------------------------
    # Private LRC
    # -------------------------
    def _testCmd(self: FhsLowLevelComponentManagerBase, task_callback: Optional[Callable] = None) -> None:
        # Assume configure fails at the start
        resultCode = ResultCode.FAILED
        taskStatus = TaskStatus.FAILED

        try:
            resultCode = (ResultCode.OK, f"Configure {self._device_id} completed OK")
            taskStatus = TaskStatus.COMPLETED
        except Exception as ex:
            resultCode = (ResultCode.FAILED, f"Unable to recover mac: {str(ex)}")
            self.set_fault_and_failed()

        task_callback(
            result=resultCode,
            status=taskStatus,
        )

    def _start(
        self: FhsLowLevelComponentManagerBase,
        task_callback: Callable,
        task_abort_event: Event,
    ) -> None:
        try:
            task_callback(status=TaskStatus.IN_PROGRESS)

            if not task_abort_event.isSet():
                # TODO Add polling
                result = self._api.start()

                if result[0] is ResultCode.OK:
                    self._set_task_callback_ok_completed(task_callback, result[1])
                else:
                    self._set_task_callback_failed(task_callback, result[1])
            else:
                self._set_task_callback_aborted(task_callback, "Start command was ABORTED")

        except Exception as ex:
            self._set_task_callback_failed(task_callback, f"Start command FAILED. ex={ex!r}")
            self.set_fault_and_failed()

    def _stop(
        self: FhsLowLevelComponentManagerBase,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        try:
            task_callback(status=TaskStatus.IN_PROGRESS)

            if not task_abort_event.is_set():
                # TODO add polling
                result = self._api.stop()
                if result[0] is ResultCode.OK:
                    self._set_task_callback_ok_completed(task_callback, result[1])
                else:
                    self._set_task_callback_failed(task_callback, result[1])
            else:
                self._set_task_callback_aborted(task_callback, "Stop command was ABORTED")

        except Exception as ex:
            self._set_task_callback_failed(task_callback, f"Stop command FAILED. ex={ex!r}")
            self.set_fault_and_failed()
