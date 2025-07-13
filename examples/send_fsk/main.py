#!/usr/bin/env python3
"""
FSK File Transmission Script for TTGO LoRa32-OLED v2.1.6

This script provides a robust interface for transmitting binary files over FSK
using the serial interface of ttgo-fsk-tx firmware. It supports configuration
of transmission parameters and includes comprehensive error handling.

Features:
    - Configurable frequency and transmit power
    - Binary file transmission up to 2048 bytes
    - Automatic device reset on timeout
    - Comprehensive error handling and validation
    - Performance-optimized serial communication

Protocol:
    Device responses follow format: XX:N:S where N=0 indicates success
    Commands:
        f <freq>   - Set frequency in MHz
        p <power>  - Set transmit power in dBm (2-17)
        m <length> - Transmit binary data of specified length

Author: Generated for TTGO FSK transmitter project
Version: 2.0
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional, Union

import serial

# Configuration constants
MAX_CHUNK = 2048  # Maximum bytes per transmission (console.cpp limit)
DEFAULT_BAUD = 115200  # Default serial baud rate (matches defaults.h)
MIN_POWER = 2  # Minimum transmit power in dBm
MAX_POWER = 17  # Maximum transmit power in dBm
DEFAULT_TIMEOUT = 30.0  # Default response timeout in seconds
SERIAL_READ_TIMEOUT = 1.0  # Serial port read timeout
DEVICE_RESET_DELAY = 2.0  # Delay after device reset
DTR_TOGGLE_DELAY = 0.1  # DTR toggle delay for reset
POLL_INTERVAL = 0.01  # Polling interval for non-blocking reads

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse and validate command line arguments.
    
    Returns:
        argparse.Namespace: Parsed and validated arguments
        
    Raises:
        SystemExit: If arguments are invalid
    """
    parser = argparse.ArgumentParser(
        description='Transmits a file over FSK using the serial interface of ttgo-fsk-tx.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /dev/ttyUSB0 data.bin
  %(prog)s COM3 packet.bin -f 433.5 -p 10
  %(prog)s /dev/ttyUSB0 message.txt -b 9600 -t 60

Supported file formats: Any binary file up to 2048 bytes
        """
    )
    
    parser.add_argument(
        'port',
        help='Serial port device (e.g., /dev/ttyUSB0, COM3)'
    )
    parser.add_argument(
        'file',
        type=Path,
        help='Path to file to transmit (max 2048 bytes)'
    )
    parser.add_argument(
        '-f', '--frequency',
        type=float,
        metavar='MHz',
        help='Frequency in MHz to set before transmission'
    )
    parser.add_argument(
        '-p', '--power',
        type=int,
        metavar='dBm',
        help=f'Transmit power in dBm ({MIN_POWER}-{MAX_POWER})'
    )
    parser.add_argument(
        '-b', '--baud',
        type=int,
        metavar='RATE',
        default=DEFAULT_BAUD,
        help=f'Serial baud rate (default: {DEFAULT_BAUD})'
    )
    parser.add_argument(
        '-t', '--timeout',
        type=float,
        metavar='SECONDS',
        default=DEFAULT_TIMEOUT,
        help=f'Response timeout in seconds (default: {DEFAULT_TIMEOUT})'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate parameters without transmitting'
    )
    
    args = parser.parse_args()
    
    # Validate power range
    if args.power is not None and not (MIN_POWER <= args.power <= MAX_POWER):
        parser.error(f'power must be between {MIN_POWER} and {MAX_POWER} dBm')
    
    # Validate frequency (basic range check)
    if args.frequency is not None and not (100.0 <= args.frequency <= 1000.0):
        parser.error('frequency must be between 100 and 1000 MHz')
    
    # Validate file existence and size
    if not args.file.is_file():
        parser.error(f"file '{args.file}' does not exist or is not a file")
    
    file_size = args.file.stat().st_size
    if file_size > MAX_CHUNK:
        parser.error(f"file size {file_size} exceeds maximum of {MAX_CHUNK} bytes")
    
    if file_size == 0:
        parser.error("file is empty")
    
    # Validate timeout
    if args.timeout <= 0:
        parser.error('timeout must be positive')
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    return args


def drain_startup(ser: serial.Serial, timeout: float = 1.0) -> List[str]:
    """
    Read and collect any startup messages from the device.
    
    This function drains the serial buffer of any startup messages that
    the device may send upon connection or reset. Messages are both
    printed to stdout and returned for potential analysis.
    
    Args:
        ser: Open serial connection to the device
        timeout: Maximum time to wait for messages in seconds
        
    Returns:
        List of startup messages received from the device
    """
    logger.debug(f"Draining startup messages (timeout: {timeout}s)")
    messages = []
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8', errors='replace').rstrip()
                if line:
                    logger.info(f"Device: {line}")
                    messages.append(line)
            except UnicodeDecodeError:
                logger.warning("Received non-UTF-8 data during startup")
        else:
            time.sleep(POLL_INTERVAL)
    
    logger.debug(f"Collected {len(messages)} startup messages")
    return messages


def send_command(ser: serial.Serial, cmd: str) -> None:
    """
    Send a console command to the device with proper encoding and logging.
    
    The command is sent with a newline terminator and logged for debugging.
    All commands are encoded as UTF-8 for reliable transmission.
    
    Args:
        ser: Open serial connection to the device
        cmd: Command string to send (without newline)
        
    Raises:
        serial.SerialException: If the serial write operation fails
    """
    try:
        command_bytes = (cmd + '\n').encode('utf-8')
        ser.write(command_bytes)
        ser.flush()  # Ensure immediate transmission
        logger.info(f"Sent command: {cmd}")
    except serial.SerialException as e:
        logger.error(f"Failed to send command '{cmd}': {e}")
        raise
    except UnicodeEncodeError as e:
        logger.error(f"Failed to encode command '{cmd}': {e}")
        raise


def read_response(ser: serial.Serial, timeout: Optional[float] = None) -> Optional[str]:
    """
    Read the next non-empty line from the serial connection.
    
    This function handles timeout, decoding errors, and empty lines gracefully.
    It returns the first non-empty line received or None if no data is available.
    
    Args:
        ser: Open serial connection to the device
        timeout: Optional timeout override for this read operation
        
    Returns:
        Decoded line string without whitespace, or None if no data
        
    Raises:
        serial.SerialException: If the serial read operation fails
    """
    original_timeout = ser.timeout
    if timeout is not None:
        ser.timeout = timeout
    
    try:
        raw = ser.readline()
        if not raw:
            return None
            
        line = raw.decode('utf-8', errors='replace').strip()
        if line:
            logger.debug(f"Received: {line}")
            return line
        return None
        
    except serial.SerialException as e:
        logger.error(f"Serial read error: {e}")
        raise
    finally:
        if timeout is not None:
            ser.timeout = original_timeout


def reset_device(ser: serial.Serial) -> None:
    """
    Reset the device using DTR signal or port reconnection.
    
    This function attempts to reset the device by toggling the DTR line,
    which triggers a hardware reset on most ESP32 development boards.
    If DTR control fails, it falls back to closing and reopening the port.
    
    Args:
        ser: Open serial connection to the device
        
    Raises:
        serial.SerialException: If both reset methods fail
    """
    logger.warning("Resetting device due to timeout or error")
    
    try:
        # Attempt DTR reset (preferred method)
        logger.debug("Attempting DTR reset")
        ser.setDTR(False)
        time.sleep(DTR_TOGGLE_DELAY)
        ser.setDTR(True)
        logger.debug("DTR reset completed")
    except (serial.SerialException, AttributeError) as e:
        # Fallback to port reconnection
        logger.debug(f"DTR reset failed ({e}), trying port reconnection")
        try:
            port = ser.port
            baudrate = ser.baudrate
            ser.close()
            time.sleep(DTR_TOGGLE_DELAY)
            ser.port = port
            ser.baudrate = baudrate
            ser.open()
            logger.debug("Port reconnection completed")
        except serial.SerialException as reconnect_error:
            logger.error(f"Device reset failed: {reconnect_error}")
            raise
    
    # Wait for device to fully restart
    time.sleep(DEVICE_RESET_DELAY)
    
    # Clear any startup messages after reset
    startup_messages = drain_startup(ser, timeout=3.0)
    if startup_messages:
        logger.info(f"Device restarted, received {len(startup_messages)} startup messages")


def expect_console_success(ser: serial.Serial, expected_msg_prefix: str, timeout: Optional[float]) -> str:
    """
    Wait for a CONSOLE:0: success response with specific message prefix.
    
    Args:
        ser: Open serial connection to the device
        expected_msg_prefix: Expected prefix of the message part
        timeout: Maximum time to wait for response in seconds
        
    Returns:
        The complete message string from the CONSOLE response
        
    Raises:
        TimeoutError: If no valid response is received within timeout
        RuntimeError: If the device returns an error response
    """
    logger.debug(f"Expecting CONSOLE:0: response with message prefix '{expected_msg_prefix}' (timeout: {timeout}s)")
    start_time = time.time()
    response_count = 0
    
    while True:
        if timeout is not None and time.time() - start_time > timeout:
            logger.error(f"No valid CONSOLE response after {timeout} seconds ({response_count} responses received)")
            reset_device(ser)
            raise TimeoutError(f'No valid CONSOLE response after {timeout} seconds')
        
        line = read_response(ser, timeout=min(1.0, timeout) if timeout else 1.0)
        if not line:
            continue
            
        response_count += 1
        logger.debug(f"Processing response #{response_count}: {line}")
        
        parts = line.split(':', 2)
        if len(parts) < 3:
            logger.debug(f"Invalid response format (expected XX:N:S): {line}")
            continue
            
        prefix, code_str, msg = parts
        
        # Only process CONSOLE messages
        if prefix != "CONSOLE":
            logger.debug(f"Ignoring non-CONSOLE message: {line}")
            continue
            
        try:
            code = int(code_str)
        except ValueError:
            logger.debug(f"Invalid response code (not integer): {code_str}")
            continue
        
        if code != 0:
            error_msg = f'Console error (code {code}): {msg}'
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        if msg.startswith(expected_msg_prefix):
            logger.debug(f"CONSOLE success response matched: {msg}")
            return msg
        
        logger.debug(f"CONSOLE response '{msg}' did not match expected prefix '{expected_msg_prefix}'")


def expect_tx_success(ser: serial.Serial, timeout: Optional[float]) -> str:
    """
    Wait for a TX:0: success response indicating transmission completion.
    
    Args:
        ser: Open serial connection to the device
        timeout: Maximum time to wait for response in seconds
        
    Returns:
        The complete message string from the TX response
        
    Raises:
        TimeoutError: If no valid response is received within timeout
        RuntimeError: If the device returns an error response
    """
    logger.debug(f"Expecting TX:0: success response (timeout: {timeout}s)")
    start_time = time.time()
    response_count = 0
    
    while True:
        if timeout is not None and time.time() - start_time > timeout:
            logger.error(f"No valid TX response after {timeout} seconds ({response_count} responses received)")
            reset_device(ser)
            raise TimeoutError(f'No valid TX response after {timeout} seconds')
        
        line = read_response(ser, timeout=min(1.0, timeout) if timeout else 1.0)
        if not line:
            continue
            
        response_count += 1
        logger.debug(f"Processing response #{response_count}: {line}")
        
        parts = line.split(':', 2)
        if len(parts) < 3:
            logger.debug(f"Invalid response format (expected XX:N:S): {line}")
            continue
            
        prefix, code_str, msg = parts
        
        # Only process TX messages
        if prefix != "TX":
            logger.debug(f"Ignoring non-TX message: {line}")
            continue
            
        try:
            code = int(code_str)
        except ValueError:
            logger.debug(f"Invalid response code (not integer): {code_str}")
            continue
        
        if code != 0:
            error_msg = f'Transmission error (code {code}): {msg}'
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.debug(f"TX success response received: {msg}")
        return msg


def expect(ser: serial.Serial, prefixes: Union[str, List[str]], timeout: Optional[float]) -> str:
    """
    Wait for a device response matching one of the specified prefixes.
    
    This function implements the core protocol for communicating with the device.
    It parses responses in the format "XX:N:S" where N=0 indicates success.
    On timeout, the device is automatically reset before raising an exception.
    
    Args:
        ser: Open serial connection to the device
        prefixes: Expected message prefix(es) to match
        timeout: Maximum time to wait for response in seconds
        
    Returns:
        The complete message string that matched one of the prefixes
        
    Raises:
        TimeoutError: If no valid response is received within timeout
        RuntimeError: If the device returns an error response (code != 0)
        serial.SerialException: If serial communication fails
    """
    if isinstance(prefixes, str):
        prefixes = [prefixes]
    
    logger.debug(f"Expecting response with prefixes: {prefixes} (timeout: {timeout}s)")
    start_time = time.time()
    response_count = 0
    
    while True:
        # Check for timeout
        if timeout is not None and time.time() - start_time > timeout:
            logger.error(f"No valid response after {timeout} seconds ({response_count} responses received)")
            reset_device(ser)
            raise TimeoutError(f'No valid response after {timeout} seconds')
        
        # Read next line
        line = read_response(ser, timeout=min(1.0, timeout) if timeout else 1.0)
        if not line:
            continue
            
        response_count += 1
        logger.debug(f"Processing response #{response_count}: {line}")
        
        # Parse response format: XX:N:S
        parts = line.split(':', 2)
        if len(parts) < 3:
            logger.debug(f"Invalid response format (expected XX:N:S): {line}")
            continue
            
        _, code_str, msg = parts
        
        # Validate response code
        try:
            code = int(code_str)
        except ValueError:
            logger.debug(f"Invalid response code (not integer): {code_str}")
            continue
        
        # Check for error response
        if code != 0:
            error_msg = f'Device error (code {code}): {msg}'
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Check if message matches any expected prefix
        for prefix in prefixes:
            if msg.startswith(prefix):
                logger.debug(f"Response matched prefix '{prefix}': {msg}")
                return msg
        
        logger.debug(f"Response '{msg}' did not match any expected prefix")


def validate_serial_port(port: str, baud: int) -> serial.Serial:
    """
    Open and validate serial port connection.
    
    Args:
        port: Serial port device path
        baud: Baud rate for communication
        
    Returns:
        Configured and open serial connection
        
    Raises:
        serial.SerialException: If port cannot be opened
    """
    logger.info(f"Opening serial port {port} at {baud} baud")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baud,
            timeout=SERIAL_READ_TIMEOUT,
            write_timeout=SERIAL_READ_TIMEOUT,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # Verify port is actually open and responsive
        if not ser.is_open:
            raise serial.SerialException("Port failed to open")
            
        logger.info(f"Serial port {port} opened successfully")
        return ser
        
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port {port}: {e}")
        raise


def configure_device(ser: serial.Serial, frequency: Optional[float], 
                    power: Optional[int], timeout: float) -> None:
    """
    Configure device transmission parameters.
    
    Args:
        ser: Open serial connection
        frequency: Frequency in MHz (if provided)
        power: Transmit power in dBm (if provided)
        timeout: Response timeout in seconds
        
    Raises:
        RuntimeError: If device configuration fails
        TimeoutError: If device doesn't respond within timeout
    """
    logger.info("Configuring device parameters")
    
    # Set transmit power if requested
    if power is not None:
        logger.info(f"Setting transmit power to {power} dBm")
        send_command(ser, f'p {power}')
        response = expect_console_success(ser, 'Transmit power set to', timeout)
        logger.debug(f"Power configuration response: {response}")
    
    # Set frequency if requested
    if frequency is not None:
        logger.info(f"Setting frequency to {frequency} MHz")
        send_command(ser, f'f {frequency}')
        response = expect_console_success(ser, 'Frequency set to', timeout)
        logger.debug(f"Frequency configuration response: {response}")
    
    logger.info("Device configuration completed")


def transmit_file(ser: serial.Serial, file_path: Path, timeout: float) -> int:
    """
    Transmit file contents to the device.
    
    Args:
        ser: Open serial connection
        file_path: Path to file to transmit
        timeout: Response timeout in seconds
        
    Returns:
        Number of bytes successfully transmitted
        
    Raises:
        RuntimeError: If transmission fails
        TimeoutError: If device doesn't respond within timeout
    """
    # Read file data
    logger.info(f"Reading file: {file_path}")
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except IOError as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise RuntimeError(f"File read error: {e}")
    
    size = len(data)
    logger.info(f"File loaded: {size} bytes")
    
    # Initiate transmission
    logger.info(f"Starting transmission of {size} bytes")
    send_command(ser, f'm {size}')
    response = expect_console_success(ser, f'Waiting for {size} bytes', timeout)
    logger.debug(f"Device ready for data: {response}")
    
    # Send binary data
    logger.debug("Sending binary data")
    try:
        bytes_written = ser.write(data)
        ser.flush()
        
        if bytes_written != size:
            raise RuntimeError(f"Partial write: {bytes_written}/{size} bytes")
            
        logger.debug(f"Binary data sent: {bytes_written} bytes")
    except serial.SerialException as e:
        logger.error(f"Failed to send binary data: {e}")
        raise RuntimeError(f"Data transmission error: {e}")
    
    # Wait for acceptance confirmation with byte count validation
    accept_response = expect_console_success(ser, f'Accepted {size} bytes', timeout)
    logger.debug(f"Data accepted: {accept_response}")
    
    # Validate the accepted byte count
    if f'Accepted {size} bytes' not in accept_response:
        logger.error(f"Device accepted wrong number of bytes: {accept_response}")
        reset_device(ser)
        raise RuntimeError(f"Device accepted wrong number of bytes: {accept_response}")
    
    # Wait for transmission completion
    tx_response = expect_tx_success(ser, timeout)
    logger.debug(f"Transmission completed: {tx_response}")
    
    logger.info(f"Transmission completed successfully: {size} bytes")
    return size


def main() -> None:
    """
    Main application entry point.
    
    Parses command line arguments, establishes serial communication,
    configures the device, and transmits the specified file.
    """
    try:
        args = parse_args()
        
        logger.info(f"FSK File Transmitter starting")
        logger.info(f"Target: {args.port} at {args.baud} baud")
        logger.info(f"File: {args.file} ({args.file.stat().st_size} bytes)")
        
        if args.dry_run:
            logger.info("Dry run mode: validation completed successfully")
            return
        
        # Open serial connection
        ser = validate_serial_port(args.port, args.baud)
        
        try:
            # Quickly drain any existing startup messages
            logger.info("Checking for device startup messages")
            startup_messages = drain_startup(ser, timeout=0.5)
            
            if startup_messages:
                logger.info(f"Device ready, received {len(startup_messages)} startup messages")
            else:
                logger.info("Device ready (no startup messages - already initialized)")
            
            # Configure transmission parameters
            configure_device(ser, args.frequency, args.power, args.timeout)
            
            # Transmit file
            bytes_sent = transmit_file(ser, args.file, args.timeout)
            
            logger.info(f"Operation completed successfully: {bytes_sent} bytes transmitted")
            
        finally:
            ser.close()
            logger.debug("Serial port closed")
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except (serial.SerialException, RuntimeError, TimeoutError) as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()