#include "gasSensorManager.h"

static const char *SENSOR_TAG = " ==SENSOR== ";

#ifndef CONFIG_GAS_ALARM_THRESHOLD
#define CONFIG_GAS_ALARM_THRESHOLD 3000
#endif

int iReadGasSensor(){
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_0, ADC_ATTEN_DB_12); // Read values from 0V to 3.3V range
    int val = adc1_get_raw(ADC1_CHANNEL_0);  // Read analog value from ADC1 channel 0
    
    return val;
}

void vSensorPollingTask(void *pvParameters) {
    ESP_LOGI(SENSOR_TAG, "Starting sensor polling task...");
    while (1) {
        // Read gas sensor value
        int gasLevel = iReadGasSensor(); // Read analog value from SENSOR_PIN

        if (gasLevel > CONFIG_GAS_ALARM_THRESHOLD) {
            // Send alarm signal if the threshold is exceeded
            int alarm_signal = 1;
            xQueueSend(alarm_queue, &alarm_signal, pdMS_TO_TICKS(1000));
        } else{
            // Send signal to turn off the alarm if its on
            int alarm_signal = 0;
            xQueueSend(alarm_queue, &alarm_signal, pdMS_TO_TICKS(1000));
        }

        // Delay before next read
        vTaskDelay(pdMS_TO_TICKS(200)); // 200ms delay
    }
}