__all__ = ["SeekCompact"]

import asyncio
from typing import Dict, Any, List
import numpy as np

from yaqd_core import HasMeasureTrigger
import usb  # type: ignore
import struct
from time import sleep


BEGIN_MEMORY_WRITE = 82
COMPLETE_MEMORY_WRITE = 81
GET_BIT_DATA = 59
GET_CURRENT_COMMAND_ARRAY = 68
GET_DATA_PAGE = 65
GET_DEFAULT_COMMAND_ARRAY = 71
GET_ERROR_CODE = 53
GET_FACTORY_SETTINGS = 88
GET_FIRMWARE_INFO = 78
GET_IMAGE_PROCESSING_MODE = 63
GET_OPERATION_MODE = 61
GET_RDAC_ARRAY = 77
GET_SHUTTER_POLARITY = 57
GET_VDAC_ARRAY = 74
READ_CHIP_ID = 54
RESET_DEVICE = 89
SET_BIT_DATA_OFFSET = 58
SET_CURRENT_COMMAND_ARRAY = 67
SET_CURRENT_COMMAND_ARRAY_SIZE = 66
SET_DATA_PAGE = 64
SET_DEFAULT_COMMAND_ARRAY = 70
SET_DEFAULT_COMMAND_ARRAY_SIZE = 69
SET_FACTORY_SETTINGS = 87
SET_FACTORY_SETTINGS_FEATURES = 86
SET_FIRMWARE_INFO_FEATURES = 85
SET_IMAGE_PROCESSING_MODE = 62
SET_OPERATION_MODE = 60
SET_RDAC_ARRAY = 76
SET_RDAC_ARRAY_OFFSET_AND_ITEMS = 75
SET_SHUTTER_POLARITY = 56
SET_VDAC_ARRAY = 73
SET_VDAC_ARRAY_OFFSET_AND_ITEMS = 72
START_GET_IMAGE_TRANSFER = 83
TARGET_PLATFORM = 84
TOGGLE_SHUTTER = 55
UPLOAD_FIRMWARE_ROW_SIZE = 79
WRITE_MEMORY_DATA = 80

sl = (slice(None, -1, None), slice(None, -2, None))


class SeekCompact(HasMeasureTrigger):
    _kind = "seek-compact"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        # 0010: Seek Thermal Compact/CompactXR
        # 0011: Seek Thermal CompactPRO -- unsupported atm
        dev = usb.core.find(idVendor=0x289D, idProduct=0x0010)
        if dev is None:
            raise ValueError("Device not found")
        self.dev = dev
        self.cal = 0
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        interface = cfg[(0, 0)]
        ep = usb.util.find_descriptor(
            interface,
            # match the first OUT endpoint
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
            == usb.util.ENDPOINT_OUT,
        )
        assert ep is not None

        self.logger.debug(f"interface {interface}")
        try:
            msg = "\x01"
            dev.ctrl_transfer(0x41, TARGET_PLATFORM, 0, 0, msg)  # 84, TARGET_PLATFORM
        except Exception as e:
            self.logger.error(e)
            self.deinit()
            msg = "\x01"
            dev.ctrl_transfer(0x41, TARGET_PLATFORM, 0, 0, msg)

        self._init_camera()
        self._channel_names = ["img"]
        self._channel_units = {"img": "counts"}
        self._channel_shapes = {"img": (155, 206)}

    def deinit(self):
        msg = "\x00\x00"
        self.logger.debug("deinit")
        for i in range(3):
            self.dev.ctrl_transfer(
                0x41, SET_OPERATION_MODE, 0, 0, msg
            )  # Set Operation Mode 0x0000 (Sleep)

    async def _measure(self):
        out = {}
        while True:
            try:
                # 0x7ec0 = 32448 = 208 x 156
                # note the 208--two extra dead rows
                self.dev.ctrl_transfer(
                    0x41, START_GET_IMAGE_TRANSFER, 0, 0, struct.pack("i", 208 * 156)
                )
            except Exception as e:
                self.logger.error(e)
                continue
            try:
                data = self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
            except usb.USBError as e:
                self.logger.error(e)
                sleep(0.1)
                continue
            # data should be a list of 16 bit data (i.e. 2 * 208 * 156 bytes)
            self.logger.debug(f"data len {len(data)}")  # 64896 = 2 * 208 * 156
            data = np.frombuffer(data, dtype=np.int16)
            img_code = data[10]
            self.logger.debug(f"img code: {img_code}")
            if img_code == 3:
                break
            elif img_code == 1:  # new cal image
                first_time = isinstance(self.cal, int)
                self.cal = data.reshape(156, 208)[sl]
                if first_time:  # find the dead pixels
                    try:
                        dmean = self.cal.mean()
                        self.dead_pixels = np.where(self.cal < 0.3 * dmean)
                        self.logger.info(
                            f"dead pixels: {[(x,y) for x,y in zip(*self.dead_pixels)]}"
                        )
                    except Exception as e:
                        self.logger.error(e)
                self.logger.debug(f"cal 0,40 = {self.cal[0,40]}")
                continue
        try:
            data = data.reshape(156, 208)[sl].astype(np.int32)
            data -= self.cal
            # self.logger.info(f"data shape {data.shape}")
            for xi, yi in zip(*self.dead_pixels):  # median filter to replace dead pixels
                xmin, xmax = max(0, xi - 1), min(xi + 2, data.shape[0] + 1)
                ymin, ymax = max(0, yi - 1), min(yi + 2, data.shape[1] + 1)
                sli = (slice(xmin, xmax, None), slice(ymin, ymax, None))
                old = data[xi, yi]
                data[xi, yi] = np.median(data[sli])
                # self.logger.info(f"{xi},{yi}: [{xmin}:{xmax},{ymin}:{ymax}] {old}->{data[xi,yi]}")
            # force pixel 1 and 40 to zero
            data[0, 1] = np.median(data[0:2, 1:3])
            data[0, 40] = np.median(data[0:2, 39:42])
        except Exception as e:
            self.logger.error(e)
        # self.logger.info(f"is 0,1 a dead pixel? cal {self.cal[0,1], data[0,1]}")
        out["img"] = data[:, ::-1]
        return out

    def _deinit(self):
        self._send_msg(0x40, SET_OPERATION_MODE, chr(0) * 2)
        # 0x3c = 60  Set Operation Mode 0x0000 (Sleep)

    def close(self):
        self.dev.reset()

    def _init_camera(self):
        self.dev.ctrl_transfer(0x41, SET_OPERATION_MODE, 0, 0, "\x00\x00")
        self.firmware_info = self.dev.ctrl_transfer(0xC1, GET_FIRMWARE_INFO, 0, 0, 4)

        self.chip_id = self.dev.ctrl_transfer(0xC1, READ_CHIP_ID, 0, 0, 12)

        self.dev.ctrl_transfer(
            0x41, SET_FACTORY_SETTINGS_FEATURES, 0, 0, "\x20\x00\x30\x00\x00\x00"
        )
        # out = dev.ctrl_transfer(0xC1, GET_FACTORY_SETTINGS, 0, 0, 64)

        self.dev.ctrl_transfer(
            0x41, SET_FACTORY_SETTINGS_FEATURES, 0, 0, "\x20\x00\x50\x00\x00\x00"
        )
        # out = dev.ctrl_transfer(0xC1, GET_FACTORY_SETTINGS, 0, 0, 64)

        self.dev.ctrl_transfer(
            0x41, SET_FACTORY_SETTINGS_FEATURES, 0, 0, "\x0C\x00\x70\x00\x00\x00"
        )
        # out = dev.ctrl_transfer(0xC1, GET_FACTORY_SETTINGS, 0, 0, 24)

        self.dev.ctrl_transfer(
            0x41, SET_FACTORY_SETTINGS_FEATURES, 0, 0, "\x06\x00\x08\x00\x00\x00"
        )
        # out = dev.ctrl_transfer(0xC1, GET_FACTORY_SETTINGS, 0, 0, 12)

        self.dev.ctrl_transfer(
            0x41, SET_IMAGE_PROCESSING_MODE, 0, 0, "\x08\x00"
        )  # Set Image Processing Mode 0x0008
        # out = dev.ctrl_transfer(0xC1, GET_OPERATION_MODE, 0, 0, 2)

        self.dev.ctrl_transfer(
            0x41, SET_IMAGE_PROCESSING_MODE, 0, 0, "\x08\x00"
        )  # Set Image Processing Mode  0x0008
        self.dev.ctrl_transfer(0x41, SET_OPERATION_MODE, 0, 0, "\x01\x00")  # 0x0001 (Run)
        # out = dev.ctrl_transfer(0xC1, GET_OPERATION_MODE, 0x3D, 0, 0, 2)
