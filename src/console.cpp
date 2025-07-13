#define RADIO_BOARD_AUTO

#include <HardwareSerial.h>
#include <RadioLib.h>
#include <RadioBoards.h>

#include "display.h"

extern Radio radio;

extern volatile bool console_loop_enable;
extern volatile bool fifo_empty;

extern uint8_t tx_data_buffer[2048];
extern int current_tx_total_length;
extern int current_tx_remaining_length;
extern int16_t radio_start_transmit_status;

extern float current_tx_frequency;
extern float current_tx_power;

String await_read_line()
{
    String result = "";
    while (true)
    {
        if (Serial.available() > 0)
        {
            char c = Serial.read();
            if (c == '\n')
            {
                return result;
            }
            result += c;
        }
    }
}

void console_loop()
{
    int state = RADIOLIB_ERR_NONE;
    String line = await_read_line();

    if (line.length() < 3 || line[1] != ' ')
    {
        Serial.println("CONSOLE:9:Unknown command");
        return;
    }

    char cmd = line[0];

    switch (cmd)
    {
    case 'f':
    {
        float freq = line.substring(2).toFloat();
        state = radio.setFrequency(freq);

        if (state != RADIOLIB_ERR_NONE)
        {
            Serial.println("CONSOLE:1:Failed to set frequency");
            return;
        }

        Serial.print("CONSOLE:0:Frequency set to ");
        Serial.println(freq, 4);

        current_tx_frequency = freq;
        display_status();

        break;
    }

    case 'p':
    {
        int power = line.substring(2).toInt();
        state = radio.setOutputPower(power);

        if (state != RADIOLIB_ERR_NONE)
        {
            Serial.println("CONSOLE:1:Failed to set transmit power");
            return;
        }

        Serial.print("CONSOLE:0:Transmit power set to ");
        Serial.println(power);

        current_tx_power = power;
        display_status();

        break;
    }

    case 'm':
    {
        int bytes_to_read = line.substring(2).toInt();

        if (bytes_to_read < 1)
        {
            Serial.println("CONSOLE:9:Invalid parameter");
            break;
        }

        if (bytes_to_read > 2048)
            bytes_to_read = 2048;

        Serial.print("CONSOLE:0:Waiting for ");
        Serial.print(bytes_to_read);
        Serial.println(" bytes");

        current_tx_total_length = 0;
        while (current_tx_total_length < bytes_to_read)
        {
            if (Serial.available())
            {
                tx_data_buffer[current_tx_total_length++] = Serial.read();
            }
        }

        Serial.print("CONSOLE:0:Accepted ");
        Serial.print(current_tx_total_length);
        Serial.println(" bytes");

        fifo_empty = true;
        console_loop_enable = false;
        current_tx_remaining_length = current_tx_total_length;
        radio_start_transmit_status = radio.startTransmit(tx_data_buffer, current_tx_total_length);

        display_status();

        break;
    }

    default:
        Serial.println("CONSOLE:9:Unknown command");
    }
}