# Bambu Lab FUID Flasher

A modern, clean Python/Tkinter graphical user interface (GUI) designed to streamline flashing and verifying Bambu Lab RFID tags using a Proxmark3 device.

## Features
* **Tag Flashing & Verification:** Easily execute `hf mf restore` and `hf mf info` commands through an intuitive GUI.
* **Library Indexing:** Index local Bambu Lab RFID tag dumps and automatically match scanned tags to their specific material and color.
* **Clipboard Integration:** Automatically copies scanned CUIDs to the clipboard.
* **Modern UI:** Built with custom card layouts, dark-themed console logging, and responsive window scaling.
* **Auto-Configuration:** Persists user settings (COM port, library paths, options) across sessions via an `.ini` file.

## Prerequisites & Requirements
* Python 3.8+
* `pyserial` (`pip install pyserial`)
* **Proxmark3 Easy:** This program is specifically designed to work with the **Proxmark3 Easy**.
* **Proxmark3 Executable:** Get the precompiled builds for Proxmark3 from [Proxmark3 Builds](https://www.proxmarkbuilds.org/) and place `proxmark3.exe` in the root directory. And copy also folder 'libs'.
* **RFID Library:** The complete Bambu Lab RFID tag library and database can be obtained from the [Bambu-Lab-RFID-Library GitHub Repository](https://github.com/queengooborg/Bambu-Lab-RFID-Library).
