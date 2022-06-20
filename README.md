# yaqd-seek

[![PyPI](https://img.shields.io/pypi/v/yaqd-seek)](https://pypi.org/project/yaqd-seek)
[![Conda](https://img.shields.io/conda/vn/conda-forge/yaqd-seek)](https://anaconda.org/conda-forge/yaqd-seek)
[![yaq](https://img.shields.io/badge/framework-yaq-orange)](https://yaq.fyi/)
[![black](https://img.shields.io/badge/code--style-black-black)](https://black.readthedocs.io/)
[![ver](https://img.shields.io/badge/calver-YYYY.M.MICRO-blue)](https://calver.org/)
[![log](https://img.shields.io/badge/change-log-informational)](https://github.com/yaq-project/yaqd-seek/-/blob/main/CHANGELOG.md)

yaq daemons for Seek thermal cameras

This package contains the following daemon(s):

- https://yaq.fyi/daemons/seek-compact

## Installation (Windows)
- install yaqd-seek and all dependencies.  
  - `conda install yaqd-seek`
- plug in device.  For me, two devices appeared (com.thermal.pir.206 and iAP interface)--no driver was found for either. I need to install a usb driver
  - download [Zadig](https://zadig.akeo.ie/)
  - select `com.thermal.pir.206` device and install `WinUSB(libusb)` driver


Maintainers:

- This package is currently unmaintained!
