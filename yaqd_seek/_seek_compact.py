__all__ = ["SeekCompact"]

import asyncio
from typing import Dict, Any, List

from yaqd_core import HasMeasureTrigger
import usb


class SeekCompact(HasMeasureTrigger):
    _kind = "seek-compact"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        # Perform any unique initialization
        dev = usb.core.find(idVendor=0x289d, idProduct=0x0010)
        if dev is None:
                raise ValueError('Device not found')
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        intf = cfg[(0,0)]

        ep = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
                lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT)

        assert ep is not None
        self.dev = dev

    async def update_state(self):
        """Continually monitor and update the current daemon state."""
        # If there is no state to monitor continuously, delete this function
        while True:
            # Perform any updates to internal state
            self._busy = False
            # There must be at least one `await` in this loop
            # This one waits for something to trigger the "busy" state
            # (Setting `self._busy = True)
            # Otherwise, you can simply `await asyncio.sleep(0.01)`
            await self._busy_sig.wait()


