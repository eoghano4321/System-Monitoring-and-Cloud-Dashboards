#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "freertos/queue.h"

#include "lwip/err.h"
#include "lwip/sys.h"

#include "driver/gpio.h"
#include "stdio.h"
#include "sdkconfig.h"
#include "driver/dac_oneshot.h"
#include "driver/adc.h"

#include <lwip/sockets.h>

#include "driver/gptimer.h"
#include "soc/timer_group_struct.h"
#include "soc/timer_group_reg.h"

#include "esp_sntp.h"
#include "esp_timer.h" // Include this header for ets_delay_us
#include "rom/ets_sys.h" // Include this header for ets_delay_us

#define SENSOR_PIN 36

#define configCHECK_FOR_STACK_OVERFLOW 2


#ifndef CONFIG_ESP_WIFI_SSID
#define CONFIG_ESP_WIFI_SSID "Other..."
#endif
#ifndef CONFIG_ESP_WIFI_PASSWORD
#define CONFIG_ESP_WIFI_PASSWORD "password1"
#endif
#ifndef CONFIG_ESP_MAXIMUM_RETRY
#define CONFIG_ESP_MAXIMUM_RETRY  10
#endif

#ifndef CONFIG_SERVER_IP
#define CONFIG_SERVER_IP "127.0.0.1"
#endif
#ifndef CONFIG_SERVER_PORT
#define CONFIG_SERVER_PORT 5665
#endif
#ifndef CONFIG_DEVICE_NAME
#define CONFIG_DEVICE_NAME "ESP32_DEVICE"
#endif

#define QUEUE_LENGTH 10
#define MAX_DATA_LEN 256

#define ESP_WIFI_SAE_MODE WPA3_SAE_PWE_HUNT_AND_PECK
#define EXAMPLE_H2E_IDENTIFIER ""
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_OPEN

#define TIMER_PERIOD_MS  5000 // How often for the hardware timer to trigger

#define HEADER_SIZE 4  // Fixed size for the length header

typedef struct {
    uint64_t event_count;
} example_queue_element_t;


/* FreeRTOS event group to signal when we are connected*/
static EventGroupHandle_t s_wifi_event_group;

/* The event group allows multiple bits for each event, but we only care about two events:
 * - we are connected to the AP with an IP
 * - we failed to connect after the maximum amount of retries */
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static const char *TAG = "=APP_MAIN=";
static const char *SOCKET_TAG = "=+=SOCKET=+=";
static const char *SENSOR_TAG = " ==SENSOR== ";

static int s_retry_num = 0;

int global_sock = -1;  // Global socket variable to maintain the connection
// Queue handle for data collection
static QueueHandle_t socket_queue = NULL;
static QueueHandle_t metrics_queue = NULL;
static QueueHandle_t alarm_queue = NULL;
gptimer_handle_t gptimer = NULL;

#define LED_PIN 9
#define ALARM_LED_PIN 10
#define GAS_THRESHOLD 2200
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

// TODO: Move this stuff to separate class
static void vWifiEventHandler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < CONFIG_ESP_MAXIMUM_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "retry to connect to the AP");
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
        ESP_LOGI(TAG,"connect to the AP fail");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void vWifiInit(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());

    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &vWifiEventHandler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &vWifiEventHandler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_ESP_WIFI_SSID,
            .password = CONFIG_ESP_WIFI_PASSWORD,
            /* Authmode threshold resets to WPA2 as default if password matches WPA2 standards (password len => 8).
             * If you want to connect the device to deprecated WEP/WPA networks, Please set the threshold value
             * to WIFI_AUTH_WEP/WIFI_AUTH_WPA_PSK and set the password with length and format matching to
             * WIFI_AUTH_WEP/WIFI_AUTH_WPA_PSK standards.
             */
            .threshold.authmode = ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD,
            .sae_pwe_h2e = ESP_WIFI_SAE_MODE,
            .sae_h2e_identifier = EXAMPLE_H2E_IDENTIFIER,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
    ESP_ERROR_CHECK(esp_wifi_start() );

    ESP_LOGI(TAG, "wifi_init_sta finished.");

    /* Waiting until either the connection is established (WIFI_CONNECTED_BIT) or connection failed for the maximum
     * number of re-tries (WIFI_FAIL_BIT). The bits are set by event_handler() (see above) */
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    /* xEventGroupWaitBits() returns the bits before the call returned, hence we can test which event actually
     * happened. */
    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "connected to ap SSID:%s password:%s",
                 CONFIG_ESP_WIFI_SSID, CONFIG_ESP_WIFI_PASSWORD);
        gpio_set_level(LED_PIN, 1);
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGI(TAG, "Failed to connect to SSID:%s, password:%s",
                 CONFIG_ESP_WIFI_SSID, CONFIG_ESP_WIFI_PASSWORD);
        gpio_set_level(LED_PIN, 0);
    } else {
        ESP_LOGE(TAG, "UNEXPECTED EVENT");
    }
}

bool bEstablishConnection() {
    ESP_LOGI(SOCKET_TAG, "Establishing connection");
    struct sockaddr_in dest_addr;
    dest_addr.sin_addr.s_addr = inet_addr(CONFIG_SERVER_IP);
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(CONFIG_SERVER_PORT);

    global_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (global_sock < 0) {
        ESP_LOGE(SOCKET_TAG, "Unable to create socket");
        return false;
    }

    if (connect(global_sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr)) != 0) {
        ESP_LOGE(SOCKET_TAG, "Socket connection failed");
        close(global_sock);
        global_sock = -1;
        return false;
    }

    ESP_LOGI(SOCKET_TAG, "Socket connected");
    return true;
}

int iCreateProtocol(const char *metrics, char **out_buffer) {
    size_t metrics_length = strlen(metrics);
    size_t device_name_length = strlen(CONFIG_DEVICE_NAME);
    size_t total_length = HEADER_SIZE + device_name_length + 1 + metrics_length;

    // Allocate memory for the protocol buffer
    char *buffer = malloc(total_length);
    if (!buffer) {
        fprintf(stderr, "Failed to allocate memory for protocol buffer.\n");
        return -1;
    }

    // Fill the header
    buffer[0] = (metrics_length >> 24) & 0xFF;
    buffer[1] = (metrics_length >> 16) & 0xFF;
    buffer[2] = (metrics_length >> 8) & 0xFF;
    buffer[3] = metrics_length & 0xFF;

    // Add the device name (null-terminated)
    memcpy(buffer + HEADER_SIZE, CONFIG_DEVICE_NAME, device_name_length + 1);

    // Add the metrics payload
    memcpy(buffer + HEADER_SIZE + device_name_length + 1, metrics, metrics_length);

    // Set the out_buffer pointer
    *out_buffer = buffer;

    return total_length;
}

int iSendMetrics(const char *metrics) {
    if (global_sock < 0) {
        // Attempt to re-establish the connection if it's lost
        if (!bEstablishConnection()) {
            ESP_LOGE(SOCKET_TAG, "Failed to re-establish connection while sending metrics. Retrying...");
            return -1;
        }
    }

    char *buffer = NULL;
    int total_length = iCreateProtocol(metrics, &buffer);
    if (total_length < 0) {
        ESP_LOGE(SOCKET_TAG, "Failed to create protocol buffer.");
        return -1;
    }

    ESP_LOGI(SOCKET_TAG, "Sending buffer: %s", buffer);

    int sent_bytes = send(global_sock, buffer, total_length, 0);
    if (sent_bytes < 0) {
        ESP_LOGE(SOCKET_TAG, "Failed to send metrics. Closing socket.");
        free(buffer);
        close(global_sock);
        global_sock = -1;
        return -1;
    }

    // Receive server response
    char respBuffer[128];
    int len = recv(global_sock, respBuffer, sizeof(respBuffer) - 1, 0);
    if (len > 0) {
        respBuffer[len] = '\0';  // Null-terminate the received data
        ESP_LOGI(SOCKET_TAG, "Server response: %s", respBuffer);

        // Act on server's response
        if (strcmp(respBuffer, "REBOOT") == 0) {
            ESP_LOGW(SOCKET_TAG, "Reboot command received. Rebooting...");
            close(global_sock);
            global_sock = -1;
            esp_restart();  // Reboot the ESP32
        } else {
            ESP_LOGI(SOCKET_TAG, "Unknown command: %s", respBuffer);
        }
    } else if (len == 0) {
        ESP_LOGW(SOCKET_TAG, "Connection closed by server.");
        close(global_sock);
        global_sock = -1;
        return -1;
    } else {
        ESP_LOGE(SOCKET_TAG, "Socket error on recv. Closing socket.");
        close(global_sock);
        global_sock = -1;
        return -1;
    }

    return 0;
}


void vSocketTask(void *pvParameters) {
    ESP_LOGI(SOCKET_TAG, "Staring socket task");

    char buffer[MAX_DATA_LEN];

    while (1) {
        ESP_LOGI(SOCKET_TAG, "=== Waiting to receive metrics to send ===");
        // Read data from the queue
        if (xQueueReceive(socket_queue, buffer, pdMS_TO_TICKS(10000)) == pdTRUE) {
            ESP_LOGI(SOCKET_TAG, "=== Received metrics to send ===");
            if (global_sock < 0) {
                if (!bEstablishConnection()) {
                    ESP_LOGE(SOCKET_TAG, "Failed to re-establish connection. Retrying...");
                    continue;
                }
            }

            // Send data over the socket
            int sent_bytes = iSendMetrics(buffer);
            if (sent_bytes < 0) {
                ESP_LOGE(SOCKET_TAG, "Failed to send data. Closing socket.");
                close(global_sock);
                global_sock = -1;  // Mark the socket as invalid
                continue;
            }

            ESP_LOGI(SOCKET_TAG, "Data sent: %s", buffer);
        }else{
            ESP_LOGE(SOCKET_TAG, "twfs");
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}


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

        if (gasLevel > GAS_THRESHOLD) {
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

static bool IRAM_ATTR bGptimerCallback(gptimer_handle_t timer, const gptimer_alarm_event_data_t *edata, void *user_data)
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
    ESP_LOGI(TAG, "Timer created successfully.");

    // Alarm configuration
    gptimer_alarm_config_t alarm_config = {
       .reload_count = 0,
       .alarm_count = TIMER_PERIOD_MS * 1000,
       .flags.auto_reload_on_alarm = true,
    };
    ESP_ERROR_CHECK(gptimer_set_alarm_action(gptimer, &alarm_config));
    ESP_LOGI(TAG, "Alarm action set.");

    // Register callback
    gptimer_event_callbacks_t cbs = {
       .on_alarm = bGptimerCallback,
    };
    ESP_ERROR_CHECK(gptimer_register_event_callbacks(gptimer, &cbs, metrics_queue));
    ESP_LOGI(TAG, "Callback registered.");

    // Enable and start the timer
    ESP_ERROR_CHECK(gptimer_enable(gptimer));
    ESP_LOGI(TAG, "Timer enabled");
    
    // Add this line to check if the timer is running
    ESP_ERROR_CHECK(gptimer_start(gptimer));
    ESP_LOGI(TAG, "Timer started");


    // Add a small delay to ensure everything is properly initialized
    vTaskDelay(pdMS_TO_TICKS(100));

    ESP_LOGI(TAG, "GPTimer setup completed successfully");
}


void app_main(void) {
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    
    xTaskCreate(vSensorPollingTask, "sensor_task", 2048, NULL, 5, NULL);
    // Create alarm task
    xTaskCreate(vAlarmTask, "alarm_task", 2048, NULL, 5, NULL);

    ESP_LOGI(TAG, "Initializing WiFi...");
    vWifiInit();

    metrics_queue = xQueueCreate(20, sizeof(example_queue_element_t));
    socket_queue = xQueueCreate(QUEUE_LENGTH, MAX_DATA_LEN);
    alarm_queue = xQueueCreate(5, sizeof(int));
    if (metrics_queue == NULL || socket_queue == NULL || alarm_queue == NULL) {
        ESP_LOGE(TAG, "Failed to create queues.");
    }


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