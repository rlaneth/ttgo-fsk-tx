#define RADIO_BOARD_AUTO

#include <RadioLib.h>
#include <RadioBoards.h>

#include "console.h"
#include "defaults.h"
#include "display.h"

Radio radio = new RadioModule();

// Global variables for transmission state
volatile bool console_loop_enable = true;                // Flag to enable/disable console input loop
volatile bool fifo_empty = false;                        // Flag set by ISR when FIFO has space for more data
volatile bool transmission_processing_complete = false;  // Flag set by fifoAdd when all data of the current transmission is sent

// Transmission data buffer and state variables
uint8_t tx_data_buffer[2048] = {0};                      // Buffer to hold the entire message data
int     current_tx_total_length = 0;                     // Total length of the current message being transmitted
int     current_tx_remaining_length = 0;                 // Number of bytes remaining to be loaded into FIFO for the current message
int16_t radio_start_transmit_status = RADIOLIB_ERR_NONE; // Stores the result of the radio.startTransmit() call

// Radio operation parameters
float current_tx_frequency = TX_FREQ_DEFAULT;            // Current transmission frequency
float current_tx_power = TX_POWER_DEFAULT;               // Current transmission power

// Panic function: halts system and displays error
void panic()
{
  display_panic();
  Serial.println("INIT:1:System halted");
  while (true)
  {
    delay(100000);
  }
}

// Interrupt Service Routine (ISR) called when radio's transmit FIFO has space.
// This function MUST be of 'void' type and MUST NOT take any arguments.
#if defined(ESP8266) || defined(ESP32)
  ICACHE_RAM_ATTR
#endif
void on_interrupt_fifo_has_space()
{
  fifo_empty = true;
}

// System setup function, runs once on boot
void setup()
{
  Serial.begin(TTGO_SERIAL_BAUD);

  display_setup();    // Initialize display
  display_status();   // Show initial status on display

  Serial.println("INIT:0:Display initialized");

  // Initialize radio module in FSK mode with specified parameters
  int radio_init_state = radio.beginFSK(current_tx_frequency,
                                     TX_BITRATE,
                                     TX_DEVIATION,
                                     RX_BANDWIDTH,
                                     current_tx_power,
                                     PREAMBLE_LENGTH,
                                     false);

  if (radio_init_state != RADIOLIB_ERR_NONE)
  {
    Serial.print("INIT:1:Radio initialization failed with code ");
    Serial.println(radio_init_state);
    panic();
  }

  // Set the callback function for when the FIFO is empty (has space)
  radio.setFifoEmptyAction(on_interrupt_fifo_has_space);

  // Configure packet mode: 0 for variable length (required for streaming)
  int packet_mode_state = radio.fixedPacketLengthMode(0);
  if (packet_mode_state != RADIOLIB_ERR_NONE) {
    Serial.print("INIT:1:Failed to set variable packet length mode, code ");
    Serial.println(packet_mode_state);
    panic();
  }

  Serial.println("INIT:0:Radio initialized successfully");
}

// Main loop, runs repeatedly
void loop()
{
  // Check if ISR indicated FIFO has space AND there's data remaining for the current transmission
  if (fifo_empty && current_tx_remaining_length > 0)
  {
    fifo_empty = false; // Reset ISR flag

    // radio.fifoAdd parameters:
    // 1. tx_data_buffer: Pointer to the start of the complete data buffer.
    // 2. current_tx_total_length: The total original length of the packet.
    // 3. &current_tx_remaining_length: Pointer to the variable holding the remaining length.
    //    RadioLib will read from tx_data_buffer at an offset calculated from total and remaining length.
    //    It updates current_tx_remaining_length with the new remaining length.
    // Returns true if the entire packet (all current_tx_total_length bytes) has been successfully loaded into the FIFO.
    transmission_processing_complete = radio.fifoAdd(tx_data_buffer, current_tx_total_length, &current_tx_remaining_length);
  }

  if (transmission_processing_complete)
  {
    transmission_processing_complete = false; // Reset flag for the next transmission cycle

    // radio_start_transmit_status holds the result from the initial radio.startTransmit() call.
    if (radio_start_transmit_status == RADIOLIB_ERR_NONE)
    {
      Serial.println("TX:0:Transmission finished successfully!");
    }
    else
    {
      // This means radio.startTransmit() itself failed.
      Serial.print("TX:1:Transmission failed to start, error code: ");
      Serial.println(radio_start_transmit_status);
    }

    // After transmission, put the radio in standby mode to stop transmitting/idling.
    // Important for FSK mode on SX127x as it might not turn off the transmitter automatically.
    radio.standby();
    Serial.println("INIT:0:Radio set to standby mode.");

    // Re-enable console for the next command and update the display.
    console_loop_enable = true;
    display_status(); // Update display (e.g., to show idle state, last status).
  }

  // If console input is enabled, run the console loop to process commands.
  if (console_loop_enable)
  {
    console_loop();
  }
}