# TTGO FSK Transmitter

FSK transmitter firmware for TTGO LoRa32-OLED v2.1.6 board with serial
control interface.

## Build

PlatformIO project for ESP32 target:

```bash
pio run                              # Build firmware
pio run --target upload             # Upload to device
pio run --target monitor            # Serial monitor
```

## Configuration

Default parameters in [src/defaults.h](src/defaults.h):

| Parameter | Value | Runtime Config |
|-----------|-------|----------------|
| Frequency | 916.0 MHz | Yes |
| TX Power | 2 dBm | Yes |
| Modulation | FSK | No |
| Deviation | 5.0 kHz | No |
| Bit Rate | 1600 bps | No |
| Serial Baud | 115200 | No |

## Serial Protocol

115200 baud, newline-terminated commands. Response format:

```
PREFIX:CODE:MESSAGE
```

- PREFIX: Message source (CONSOLE, TX, LO)
- CODE: 0=success, non-zero=error
- MESSAGE: Status text

### Commands

#### `f <MHz>` - Set Frequency
```
> f 433.5
< CONSOLE:0:Frequency set to 433.5000
```

#### `p <dBm>` - Set Power (2-17 dBm)
```
> p 10
< CONSOLE:0:Transmit power set to 10
```

#### `m <bytes>` - Transmit Data (1-2048 bytes)
```
> m 5
< CONSOLE:0:Waiting for 5 bytes
(send binary data)
< CONSOLE:0:Accepted 5 bytes
< TX:0:Transmission finished successfully!
```

### Error Responses
```
CONSOLE:1:Failed to set frequency
CONSOLE:9:Unknown command
TX:1:Transmission failed to start, error code: -2
```

## Transmission Flow

1. Send `m <size>` command
2. Wait for `CONSOLE:0:Waiting for N bytes`
3. Send N bytes of binary data
4. Wait for `CONSOLE:0:Accepted N bytes`
5. Wait for `TX:0:Transmission finished successfully!`

Device automatically starts transmission after accepting data.

## Python Example

Located in `examples/send_fsk/`. Implements complete protocol with error
handling and device reset on timeout.

### Setup
```bash
cd examples/send_fsk
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage
```bash
python main.py /dev/ttyUSB0 file.bin
python main.py /dev/ttyUSB0 file.bin -f 433.5 -p 10 -v
```

The script validates response codes and message prefixes, distinguishing
between CONSOLE responses (parameter setting, data acceptance) and TX
responses (transmission completion). Automatic device reset occurs on
communication failures or timeouts.

## License

This project is released into the public domain under [The Unlicense](LICENSE).

## Disclaimer

This is experimental firmware. Users are responsible for ensuring compliance
with local radio transmission regulations and licensing requirements.
