from __future__ import annotations

import logging
import threading
from typing import Callable

from ska_control_model import HealthState

from ska_mid_cbf_fhs_common.base_classes.api.fhs_base_api_interface import FhsBaseApiInterface
from ska_mid_cbf_fhs_common.services.health.register_polling_thread import RegisterPollingThread


class FhsHealthMonitor:
    def __init__(
        self,
        logger: logging.Logger,
        get_device_health_state: Callable,
        update_health_state_callback: Callable,
        check_registers_callback: Callable | None = None,
        api: FhsBaseApiInterface | None = None,
        status_func: str = "status",
        poll_interval=1.0,
    ) -> None:
        self._last_health_state = HealthState.UNKNOWN
        self.lock = threading.Lock()
        self.component_statuses: dict[str, HealthState] = {}

        self.logger = logger
        self.api = api
        self.check_registers_callback = check_registers_callback

        self.get_device_health_state = get_device_health_state
        self.update_health_state_callback = update_health_state_callback
        self.status_func = status_func
        self.poll_interval = poll_interval

        self._health_states = [HealthState.FAILED, HealthState.DEGRADED, HealthState.UNKNOWN, HealthState.OK]
        self._polling_thread = None

    def start_polling(self: FhsHealthMonitor):
        if self.api and self.check_registers_callback:
            if self._polling_thread is None:
                self._init_polling_thread()
                self._polling_thread.start()
        else:
            self.logger.warning(
                "Unable to start polling, health monitor not configured with an api or callback function for checking registers"
            )

    def stop_polling(self: FhsHealthMonitor):
        if self._polling_thread:
            if self._polling_thread is None or not self._polling_thread.is_alive():
                self.logger.warning("Cannot stop the polling thread, polling thread is not started.")
                return

            self._polling_thread.stop()

            if self._polling_thread is not None and self._polling_thread.is_alive():
                if self._polling_thread.ident != threading.get_ident():
                    self._polling_thread.join()
            self._polling_thread = None

    def add_health_state(self: FhsHealthMonitor, key: str, health_state: HealthState):
        with self.lock:
            if key and health_state is not None:
                self.component_statuses[key] = health_state
            else:
                raise ValueError(
                    "Key must be provided when single health state added, No key to be supplied when using dict of healthstates"
                )

            self.determine_health_state()

    def merge_health_states(self: FhsHealthMonitor, dict_to_merge: dict[str, HealthState]):
        with self.lock:
            self.component_statuses.update(dict_to_merge)
            self.determine_health_state()

    def remove_failure(self: FhsHealthMonitor, key: str):
        with self.lock:
            if key in self.component_statuses:
                self.component_statuses.pop(key)
                self.determine_health_state()

    def reset_failures(self: FhsHealthMonitor):
        self.component_statuses = {}

    def determine_health_state(self: FhsHealthMonitor):
        for health_state in self._health_states:
            if health_state in self.component_statuses.values():
                if health_state is not self.get_device_health_state():
                    self._last_health_state = health_state
                    self.update_health_state_callback(health_state)
                break

    def _init_polling_thread(self: FhsHealthMonitor) -> RegisterPollingThread:
        self._polling_thread = RegisterPollingThread(
            logger=self.logger,
            api=self.api,
            status_func=self.status_func,
            check_registers_callback=self.check_registers_callback,
            poll_interval=self.poll_interval,
            add_health_state=self.add_health_state,
            merge_health_states=self.merge_health_states,
        )
