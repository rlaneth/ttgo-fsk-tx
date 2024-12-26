# ttgo-fsk-tx

A simple FSK transmitter firmware for the TTGO LoRa32-OLED v2.1.6 board. This
project provides an interactive terminal interface to control FSK transmission
parameters and send binary data.

## Default Parameters

- Modulation: FSK
- Frequency: 916 MHz
- Frequency Deviation: 5 kHz
- Baud Rate: 1600
- TX Power: 2 dBm

Set in [defaults.h](src/defaults.h).

## Serial Interface

The firmware exposes a terminal interface over serial at 115200 baud. The
following commands are available:

### Commands

- `f <frequency>`: Set the transmit frequency in MHz

  - Example: `f 915.5` sets frequency to 915.5 MHz

- `p <power>`: Set the transmit power in dBm

  - Example: `p 15` sets TX power to 15 dBm

- `m <length>`: Transmit binary data of specified length in bytes
  - Example: `m 8` prepares to transmit 8 bytes
  - Maximum length is 2048 bytes
  - After entering this command, send the binary data immediately
  - The terminal will wait until it receives the specified number of bytes, then
    transmit it

### Notes

- Frequency and TX power can be adjusted dynamically through the terminal
- Other parameters (deviation, baud rate) are fixed and cannot be modified
  without rebuilding the firmware
- The terminal will block while waiting for binary data after the `m` command

## License

This project is released into the public domain under [The Unlicense](LICENSE).

## Disclaimer

This is experimental firmware. Users are responsible for ensuring compliance
with local radio transmission regulations and licensing requirements.
