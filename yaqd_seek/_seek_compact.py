__all__ = ["SeekCompact"]

import asyncio
from typing import Dict, Any, List
import numpy as np

from yaqd_core import HasMeasureTrigger
import usb, struct


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
        self._channel_shapes = {"img": (156, 208)}

    def deinit(self):
        msg = "\x00\x00"
        self.logger.debug("deinit")
        for i in range(3):
            self.dev.ctrl_transfer(
                0x41, SET_OPERATION_MODE, 0, 0, msg
            )  # Set Operation Mode 0x0000 (Sleep)

    async def _measure(self):
        self.logger.debug("MEASURING")
        out = {}
        while True:
            try:
                # 0x7ec0 = 32448 = 208 x 156  # note the 208--two rows not mentioned in docs--probably just dead
                self.dev.ctrl_transfer(
                    0x41,
                    START_GET_IMAGE_TRANSFER,
                    0,
                    0,
                    struct.pack("i", 208 * 156),  # '\xC0\x7E\x00\x00'
                )
            except Exception as e:
                self.logger.error(e)
                continue
            try:
                data = self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
                data += self.dev.read(0x81, 0x3F60, 1000)
            except Exception as e:  # usb.USBError as e:
                self.logger.error(e)
            self.logger.debug(f"data type: {type(data)}")
            self.logger.info(f"data len {len(data)}")  # 64896 = 2 * 208 * 156
            data = np.frombuffer(data, dtype=np.uint16)
            img_code = data[10]
            self.logger.info(f"img code: {img_code}")
            if img_code == 1:  # new cal image
                self.logger.info("new cal")
                self.cal = data.reshape(156, -1)
                self.logger.info(f"data {data[:20]}")
                continue
            if img_code == 3:
                break
        try:
            self.logger.info(f"data {data[:20]}")
            # data is a list of 16 bit data (i.e. 2 * 208 * 156 bytes)
            out["img"] = data.reshape(156, -1) + 1200 - self.cal
            self.logger.info(f"data shape {data.shape}")
        except Exception as e:
            self.logger.error(e)
        return out

    def _deinit(self):
        self._send_msg(0x40, SET_OPERATION_MODE, chr(0) * 2)
        # 0x3c = 60  Set Operation Mode 0x0000 (Sleep)

    def close(self):
        # atm it doesn't seem like I need to do anything special
        self.dev.reset()
        pass

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
