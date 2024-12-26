
#include <U8g2lib.h>

#define FONT_DEFAULT u8g2_font_7x13_tr
#define FONT_BOLD u8g2_font_7x13B_tr
#define FONT_LINE_HEIGHT 14
#define FONT_TAB_START 42

U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

extern volatile bool console_loop_enable;
extern float tx_frequency;
extern float tx_power;

void display_panic()
{
    const int centerX = display.getWidth() / 2;
    const int centerY = display.getHeight() / 2;

    const char *message = "System halted";

    display.clearBuffer();

    display.setFont(u8g2_font_open_iconic_check_4x_t);
    display.drawGlyph(centerX - (32 / 2), centerY + (32 / 2), 66);

    display.setFont(u8g2_font_nokiafc22_tr);
    int width = display.getStrWidth(message);
    display.drawStr(centerX - (width / 2), centerY + 30, message);

    display.sendBuffer();
}

void display_setup()
{
    display.begin();
    display.clearBuffer();
}

void display_status()
{

    String tx_power_str = "+";
    String tx_frequency_str = String(tx_frequency, 4);

    tx_power_str.concat(String(tx_power, 0));
    tx_power_str.concat(" dBm");
    tx_frequency_str.concat(" MHz");

    u8g2_uint_t height_ptr = display.getHeight() - 8;

    display.clearBuffer();

    display.setFont(FONT_DEFAULT);

    if (console_loop_enable)
    {
        display.drawStr(0, height_ptr, "Standby");
    }
    else
    {
        display.drawStr(0, height_ptr, "Transmitting...");
    }

    height_ptr -= FONT_LINE_HEIGHT;

    display.setFont(FONT_BOLD);
    display.drawStr(0, height_ptr, "Pwr:");

    display.setFont(FONT_DEFAULT);
    display.drawStr(FONT_TAB_START, height_ptr, tx_power_str.c_str());

    height_ptr -= FONT_LINE_HEIGHT;

    display.setFont(FONT_BOLD);
    display.drawStr(0, height_ptr, "Freq:");

    display.setFont(FONT_DEFAULT);
    display.drawStr(FONT_TAB_START, height_ptr, tx_frequency_str.c_str());

    display.setFont(FONT_BOLD);

    display.sendBuffer();
}