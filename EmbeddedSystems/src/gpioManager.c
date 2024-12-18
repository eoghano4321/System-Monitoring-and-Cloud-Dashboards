#include "gpioManager.h"
#include "driver/gpio.h"
#include "esp_log.h"

#ifndef LED_PIN
#define LED_PIN 9
#endif
#ifndef ALARM_LED_PIN
#define ALARM_LED_PIN 10
#endif
static const char *TAG = "GPIO_MANAGER";
int alarming = 0;

// Setup GPIO for LED and HC-SR04
void vGpioInit() {
    ESP_LOGI(TAG, "Setting up GPIO...");
    // Configure LED_PIN as output
    gpio_reset_pin(LED_PIN);
    gpio_reset_pin(ALARM_LED_PIN);
    esp_rom_gpio_pad_select_gpio(LED_PIN);
    esp_rom_gpio_pad_select_gpio(ALARM_LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(ALARM_LED_PIN, GPIO_MODE_OUTPUT);
}

// Debug function to show if wifi is connected successfully
void vToggleAlarm(int level)
{
    alarming = level;
    gpio_set_level(ALARM_LED_PIN, level);
}