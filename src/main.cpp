#define TTGO_SERIAL_BAUD 115200

#define TX_FREQ_DEFAULT 916.0
#define TX_BITRATE 1.6
#define TX_DEVIATION 5
#define TX_POWER_DEFAULT 2

#define RADIO_BOARD_AUTO

#include <RadioLib.h>
#include <RadioBoards.h>
#include <U8g2lib.h>

U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

Radio radio = new RadioModule();
int txState = RADIOLIB_ERR_NONE;
volatile bool fifoEmpty = false;
bool finishFlag = false;
bool commandLoopFlag = true;

uint8_t txData[2048] = {0};
int txLength = 0;
int txRemain = 0;

void panic()
{
  const char *message = "System halted";

  int centerX = display.getWidth() / 2;
  int centerY = display.getHeight() / 2;

  display.clearBuffer();

  display.setFont(u8g2_font_open_iconic_check_4x_t);
  display.drawGlyph(centerX - (32 / 2), centerY + (32 / 2), 66);

  display.setFont(u8g2_font_nokiafc22_tr);
  int width = display.getStrWidth(message);
  display.drawStr(centerX - (width / 2), centerY + 30, message);

  display.sendBuffer();

  Serial.print("! ");
  Serial.println(message);

  while (true)
  {
    delay(100000);
  }
}

void onFifoEmpty()
{
  fifoEmpty = true;
}

String readCommand()
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

void commandLoop()
{
  int state = RADIOLIB_ERR_NONE;
  String line = readCommand();

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

    break;
  }

  case 'm':
  {
    int bytesToRead = line.substring(2).toInt();

    if (bytesToRead > 2048)
      bytesToRead = 2048;

    Serial.print("__:0:Waiting for ");
    Serial.print(bytesToRead);
    Serial.println(" bytes");

    txLength = 0;
    while (txLength < bytesToRead)
    {
      if (Serial.available())
      {
        txData[txLength++] = Serial.read();
      }
    }

    Serial.print("__:0:Accepted ");
    Serial.print(txLength);
    Serial.println(" bytes");

    commandLoopFlag = false;
    txRemain = txLength;
    txState = radio.startTransmit(txData, txLength);

    break;
  }

  default:
    Serial.println("__:9:Unknown command");
  }
}

void setup()
{
  Serial.begin(TTGO_SERIAL_BAUD);

  display.begin();
  display.clearBuffer();

  Serial.println("LO:0:Display initialized");

  int state = radio.beginFSK(TX_FREQ_DEFAULT,
                             TX_BITRATE,
                             TX_DEVIATION,
                             10.4,
                             TX_POWER_DEFAULT,
                             0,
                             false);

  if (state != RADIOLIB_ERR_NONE)
  {
    Serial.print("LO:1:Radio initialization failed with code ");
    Serial.println(state);
    panic();
  }

  radio.setFifoEmptyAction(onFifoEmpty);
  radio.fixedPacketLengthMode(0);

  Serial.println("LO:0:Radio initialized");
}

void loop()
{
  if (fifoEmpty)
  {
    fifoEmpty = false;
    finishFlag = radio.fifoAdd(txData, txLength, &txRemain);
  }

  if (finishFlag)
  {
    finishFlag = false;
    txRemain = txLength;

    if (txState == RADIOLIB_ERR_NONE)
    {
      Serial.println("TX:0:Transmitted successfully");
    }
    else
    {
      Serial.println("TX:1:Transmission failed with code ");
      Serial.print(txState);
    }

    radio.standby();
    commandLoopFlag = true;
  }

  if (commandLoopFlag)
  {
    commandLoop();
  }
}