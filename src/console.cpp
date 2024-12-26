#define RADIO_BOARD_AUTO

#include <HardwareSerial.h>
#include <RadioLib.h>
#include <RadioBoards.h>

#include "display.h"

extern Radio radio;

extern volatile bool console_loop_enable;
extern volatile bool fifo_empty;

extern uint8_t tx_data[2048];
extern int tx_length;
extern int tx_remain;
extern int16_t tx_state;

extern float tx_frequency;
extern float tx_power;

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
        Serial.println("__:9:Unknown command");
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
            Serial.println("__:1:Failed to set frequency");
            return;
        }

        Serial.print("__:0:Frequency set to ");
        Serial.println(freq, 4);

        tx_frequency = freq;
        display_status();

        break;
    }

    case 'p':
    {
        int power = line.substring(2).toInt();
        state = radio.setOutputPower(power);

        if (state != RADIOLIB_ERR_NONE)
        {
            Serial.println("__:1:Failed to set transmit power");
            return;
        }

        Serial.print("__:0:Transmit power set to ");
        Serial.println(power);

        tx_power = power;
        display_status();

        break;
    }

    case 'm':
    {
        int bytes_to_read = line.substring(2).toInt();

        if (bytes_to_read < 1)
        {
            Serial.println("__:9:Invalid parameter");
            break;
        }

        if (bytes_to_read > 2048)
            bytes_to_read = 2048;

        Serial.print("__:0:Waiting for ");
        Serial.print(bytes_to_read);
        Serial.println(" bytes");

        tx_length = 0;
        while (tx_length < bytes_to_read)
        {
            if (Serial.available())
            {
                tx_data[tx_length++] = Serial.read();
            }
        }

        Serial.print("__:0:Accepted ");
        Serial.print(tx_length);
        Serial.println(" bytes");

        console_loop_enable = false;
        tx_remain = tx_length;
        tx_state = radio.startTransmit(tx_data, tx_length);

        display_status();

        break;
    }

    default:
        Serial.println("__:9:Unknown command");
    }
}