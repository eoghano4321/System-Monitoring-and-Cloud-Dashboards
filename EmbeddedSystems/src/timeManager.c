#include "timeManager.h"


static const char *SENSOR_TAG = "==SENSOR==";
gptimer_handle_t gptimer = NULL;
QueueHandle_t metrics_queue = NULL;

void vSntpInit(void) {
    ESP_LOGI(SENSOR_TAG, "Initializing SNTP");
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "pool.ntp.org");
    esp_sntp_init();
}

void vObtainTime(void) {
    vSntpInit();

    time_t now = 0;
    struct tm timeinfo = { 0 };
    int retry = 0;
    const int retry_count = 10;

    while (timeinfo.tm_year < (2016 - 1900) && ++retry < retry_count) {
        ESP_LOGI(SENSOR_TAG, "Waiting for system time to be set... (%d/%d)", retry, retry_count);
        vTaskDelay(2000 / portTICK_PERIOD_MS);
        time(&now);
        localtime_r(&now, &timeinfo);
    }

    if (retry == retry_count) {
        ESP_LOGW(SENSOR_TAG, "Failed to get time from NTP server.");
    } else {
        ESP_LOGI(SENSOR_TAG, "Time successfully synchronized");
    }
}

bool IRAM_ATTR bGptimerCallback(gptimer_handle_t timer, const gptimer_alarm_event_data_t *edata, void *user_data)
{
    BaseType_t high_task_awoken = pdFALSE;
    QueueHandle_t queue = (QueueHandle_t)user_data;
    // Retrieve count value and send to queue
    example_queue_element_t ele = {
        .event_count = edata->count_value
    };
    xQueueSendFromISR(queue, &ele, &high_task_awoken);
    // return whether we need to yield at the end of ISR
    return (high_task_awoken == pdTRUE);
}

void vGptimerInit(void) {
    // Timer configuration
    gptimer_config_t timer_config = {
       .clk_src = GPTIMER_CLK_SRC_DEFAULT,
       .direction = GPTIMER_COUNT_UP,
       .resolution_hz = 1 * 1000 * 1000
    };

    ESP_ERROR_CHECK(gptimer_new_timer(&timer_config, &gptimer));
    ESP_LOGI(SENSOR_TAG, "Timer created successfully.");

    // Alarm configuration
    gptimer_alarm_config_t alarm_config = {
       .reload_count = 0,
       .alarm_count = TIMER_PERIOD_MS * 1000,
       .flags.auto_reload_on_alarm = true,
    };
    ESP_ERROR_CHECK(gptimer_set_alarm_action(gptimer, &alarm_config));
    ESP_LOGI(SENSOR_TAG, "Alarm action set.");

    // Register callback
    gptimer_event_callbacks_t cbs = {
       .on_alarm = bGptimerCallback,
    };
    ESP_ERROR_CHECK(gptimer_register_event_callbacks(gptimer, &cbs, metrics_queue));
    ESP_LOGI(SENSOR_TAG, "Callback registered.");

    // Enable and start the timer
    ESP_ERROR_CHECK(gptimer_enable(gptimer));
    ESP_LOGI(SENSOR_TAG, "Timer enabled");
    
    // Add this line to check if the timer is running
    ESP_ERROR_CHECK(gptimer_start(gptimer));
    ESP_LOGI(SENSOR_TAG, "Timer started");


    // Add a small delay to ensure everything is properly initialized
    vTaskDelay(pdMS_TO_TICKS(100));

    ESP_LOGI(SENSOR_TAG, "GPTimer setup completed successfully");
}