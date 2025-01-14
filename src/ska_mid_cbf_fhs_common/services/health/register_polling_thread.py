from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from ska_control_model import HealthState

from ska_mid_cbf_fhs_common.base_classes.api.fhs_base_api_interface import FhsBaseApiInterface


class RegisterPollingThread(threading.Thread):
    def __init__(
        self: RegisterPollingThread,
        logger: logging.Logger,
        api: FhsBaseApiInterface,
        status_func: str,
        check_registers_callback: Callable,
        add_health_state: Callable,
        merge_health_states: Callable,
        poll_interval=1.0,
    ):
        super().__init__()
        self.logger = logger
        self.api = api
        self.status_func = status_func
        self.check_registers_callback = check_registers_callback
        self.poll_interval = poll_interval
        self.daemon = True
        self._stop_event = threading.Event()
        self.add_health_state = add_health_state
        self.merge_health_states = merge_health_states
        self._is_running = False

    def run(self: RegisterPollingThread):
        while not self._stop_event.is_set():
            try:
                time.sleep(self.poll_interval)
                status_func = getattr(self.api, self.status_func)

                _, status = status_func()

                health_states: dict[str, HealthState] = self.check_registers_callback(status)
                self.merge_health_states(health_states)
            except Exception as ex:
                self.add_health_state("REGISTER_POLLING_EXCEPTION", HealthState.UNKNOWN)
                self.stop()
                print(f"Error - Unable to monitor health. {repr(ex)}")
                raise ex

    def stop(self):
        self._stop_event.set()
