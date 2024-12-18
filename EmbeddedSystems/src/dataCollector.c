#include "dataCollector.h"
#include "gasSensorManager.h"


static const char *SENSOR_TAG = " ==SENSOR== ";

// Task to collect data from a temperature sensor
void vDataCollectionTask(void *pvParameters) {
    int signal;
    char buffer[MAX_DATA_LEN];
    ESP_LOGI(SENSOR_TAG, "STARTING METRIC COLLECTION");

    // Synchronise time
    vObtainTime();

    while (1) {
        ESP_LOGI(SENSOR_TAG, "=== Waiting for ISR ===");
        if (xQueueReceive(metrics_queue, &signal, pdMS_TO_TICKS(2000)) == pdTRUE) {
            ESP_LOGI(SENSOR_TAG, "===  Received Signal from ISR ===");
            
            float gasLevel = iReadGasSensor();

            // Get current timestamp
            time_t now;
            time(&now);
            struct tm timeinfo;
            setenv("TZ", "UTC", 1); // Set timezone to UTC
            tzset();
            localtime_r(&now, &timeinfo);
            char strftime_buf[64];
            strftime(strftime_buf, sizeof(strftime_buf), "%Y-%m-%d %H:%M:%S", &timeinfo);
            ESP_LOGI(SENSOR_TAG, "Current timestamp: %s", strftime_buf);

            snprintf(buffer, sizeof(buffer), "{\"Alarming\": {\"value\": %d}, \"gas\": {\"value\": %.2f, \"threshold\": %d}, \"timestamp\": \"%s\"}", alarming, gasLevel, 4000, strftime_buf);
            ESP_LOGI(SENSOR_TAG, "Collected data: %s", buffer);


            // Send data to the queue
            if (xQueueSend(socket_queue, buffer, pdMS_TO_TICKS(1000)) != pdPASS) {
                ESP_LOGW(SENSOR_TAG, "Failed to send data to the queue");
            }

        }else {
            ESP_LOGW(SENSOR_TAG, "twfs"); // Timeout waiting for signal
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}