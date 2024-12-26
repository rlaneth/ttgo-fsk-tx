#define RADIO_BOARD_AUTO

#include <RadioLib.h>
#include <RadioBoards.h>

#include "console.h"
#include "defaults.h"
#include "display.h"

Radio radio = new RadioModule();

volatile bool console_loop_enable = true;
volatile bool fifo_empty = false;
volatile bool tx_done = false;

uint8_t tx_data[2048] = {0};
int tx_length = 0;
int tx_remain = 0;
int16_t tx_state = RADIOLIB_ERR_NONE;

float tx_frequency = TX_FREQ_DEFAULT;
float tx_power = TX_POWER_DEFAULT;

void panic()
{
  const char *message = "System halted";

  display_panic();

  Serial.print("LO:1:System halted");

  while (true)
  {
    delay(100000);
  }
}

void on_fifo_empty()
{
  fifo_empty = true;
}

void setup()
{
  Serial.begin(TTGO_SERIAL_BAUD);

  display_setup();
  display_status();

  Serial.println("LO:0:Display initialized");

  int state = radio.beginFSK(tx_frequency,
                             TX_BITRATE,
                             TX_DEVIATION,
                             10.4,
                             tx_power,
                             0,
                             false);

  if (state != RADIOLIB_ERR_NONE)
  {
    Serial.print("LO:1:Radio initialization failed with code ");
    Serial.println(state);
    panic();
  }

  radio.setFifoEmptyAction(on_fifo_empty);
  radio.fixedPacketLengthMode(0);

  Serial.println("LO:0:Radio initialized");
}

void loop()
{
  if (fifo_empty)
  {
    fifo_empty = false;
    tx_done = radio.fifoAdd(tx_data, tx_length, &tx_remain);
  }

  if (tx_done)
  {
    tx_done = false;
    tx_remain = tx_length;

    if (tx_state == RADIOLIB_ERR_NONE)
    {
      Serial.println("TX:0:Transmitted successfully");
    }
    else
    {
      Serial.println("TX:1:Transmission failed with code ");
      Serial.print(tx_state);
    }

    radio.standby();
    console_loop_enable = true;
    display_status();
  }

  if (console_loop_enable)
  {
    console_loop();
  }
}