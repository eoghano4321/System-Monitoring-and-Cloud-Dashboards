#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "nvs_flash.h"
#include "freertos/queue.h"

#include "dataCollector.h"
#include "wifiManager.h"
#include "timeManager.h"
#include "gpioManager.h"
#include "socketManager.h"
#include "gasSensorManager.h"

#include "lwip/err.h"
#include "lwip/sys.h"

#include "driver/gpio.h"
#include "stdio.h"
#include "sdkconfig.h"
#include "driver/dac_oneshot.h"
#include "driver/adc.h"

#include <lwip/sockets.h>

#include "soc/timer_group_struct.h"
#include "soc/timer_group_reg.h"


#define SENSOR_PIN 36

#define configCHECK_FOR_STACK_OVERFLOW 2

#ifndef CONFIG_SERVER_IP
#define CONFIG_SERVER_IP "127.0.0.1"
#endif
#ifndef CONFIG_SERVER_PORT
#define CONFIG_SERVER_PORT 5665
#endif

#define QUEUE_LENGTH 10
#define MAX_DATA_LEN 256



static const char *TAG = "=APP_MAIN=";

// Queue handle for data collection
QueueHandle_t alarm_queue = NULL;


// Alarm task to process ISR signals
void vAlarmTask(void *pvParameters) {
    int alarm_signal;
    while (1) {
        if (xQueueReceive(alarm_queue, &alarm_signal, pdMS_TO_TICKS(5000))) {
            vToggleAlarm(alarm_signal); // Toggle alarm based on signal
        } else{
            ESP_LOGI(TAG, "No alarm");
        }
    }
}


void app_main(void) {
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);


    metrics_queue = xQueueCreate(20, sizeof(example_queue_element_t));
    socket_queue = xQueueCreate(QUEUE_LENGTH, MAX_DATA_LEN);
    alarm_queue = xQueueCreate(5, sizeof(int));
    if (metrics_queue == NULL || socket_queue == NULL || alarm_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create queues.");
    }


    
    xTaskCreate(vSensorPollingTask, "sensor_task", 2048, NULL, 5, NULL);
    // Create alarm task
    xTaskCreate(vAlarmTask, "alarm_task", 2048, NULL, 5, NULL);

    ESP_LOGI(TAG, "Initializing WiFi...");
    vWifiInit();

    // Setup GPIO for LED and HC-SR04
    vGpioInit();
    ESP_LOGI(TAG, "GPIO setup complete");

    // Start the hardware timer
    vGptimerInit();
    ESP_LOGI(TAG, "Set up Timer");
    
    /////////////////////////////////////////////
    //              Create tasks               //
    /////////////////////////////////////////////
    xTaskCreatePinnedToCore(vSocketTask, "socket_task", 4096, NULL, 5, NULL, 1);
    xTaskCreate(vDataCollectionTask, "data_collection_task", 8192, NULL, 5, NULL);
}