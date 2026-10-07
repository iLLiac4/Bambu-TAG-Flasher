# Bambu Lab FUID Flasher

A modern, clean Python/Tkinter graphical user interface (GUI) designed to streamline flashing and verifying Bambu Lab RFID tags using a Proxmark3 device.

## Features
* **Tag Flashing & Verification:** Easily execute `hf mf restore` and `hf mf info` commands through an intuitive GUI.
* **Library Indexing:** Index local Bambu Lab RFID tag dumps and automatically match scanned tags to their specific material and color.
* **Clipboard Integration:** Automatically copies scanned CUIDs to the clipboard.
* **Modern UI:** Built with custom card layouts, dark-themed console logging, and responsive window scaling.
* **Auto-Configuration:** Persists user settings (COM port, library paths, options) across sessions via an `.ini` file.

## Prerequisites
* Python 3.8+
* `pyserial` (`pip install pyserial`)
* [Proxmark3 Iceman Firmware](https://github.com/RfidResearchGroup/proxmark3) (`proxmark3.exe` executable placed in the root directory).
