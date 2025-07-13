# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Environment

For operations with Python scripts, if there exists a `venv` directory within
the same folder as
the script, ensure that the venv is activated.

## Build Commands

This is a PlatformIO project for ESP32. Use these commands:

- `pio run` - Build the firmware
- `pio run --target upload` - Build and upload to connected device
- `pio run --target monitor` - Open serial monitor (115200 baud)
- `pio run --target upload --target monitor` - Upload and monitor

## Architecture

This is FSK transmitter firmware for TTGO LoRa32-OLED v2.1.6 board with these
key components:

### Core Files

- `src/main.cpp` - Main application with radio setup, interrupt handling, and
  transmission logic
- `src/console.cpp` - Serial terminal interface for user commands (f, p, m)
- `src/display.cpp` - OLED display control and status updates
- `src/defaults.h` - Default radio parameters (frequency, power, deviation,
  etc.)

### Key Architecture Points

- Uses RadioLib for LoRa/FSK radio control
- Interrupt-driven transmission with FIFO management
- Global state variables for transmission control:
  - `console_loop_enable` - Controls console input processing
  - `fifo_empty` - Set by ISR when FIFO has space
  - `transmission_processing_complete` - Marks transmission completion
- 2048-byte transmission buffer for binary data
- Serial interface at 115200 baud with three commands:
  - `f <freq>` - Set frequency in MHz
  - `p <power>` - Set TX power in dBm  
  - `m <length>` - Transmit binary data (waits for exact byte count)

### Dependencies

- RadioLib 7.1.0 - Radio control library
- U8g2 - OLED display library
- RadioBoards - Board-specific configurations

The firmware provides real-time parameter adjustment through serial terminal
while maintaining fixed modulation parameters (1600 baud FSK, 5kHz deviation)
that require rebuild to change.