#include "socketManager.h"
#include "lwip/sockets.h"
#include "esp_log.h"

#ifndef CONFIG_SERVER_IP
#define CONFIG_SERVER_IP "127.0.0.1"
#endif
#ifndef CONFIG_SERVER_PORT
#define CONFIG_SERVER_PORT 5665
#endif

#define HEADER_SIZE 4  // Fixed size for the length header

#ifndef CONFIG_DEVICE_NAME
#define CONFIG_DEVICE_NAME "ESP32_DEVICE"
#endif

static const char *TAG = "SOCKET_MANAGER";
int global_sock = -1;  // Global socket variable
QueueHandle_t socket_queue = NULL;

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

bool bEstablishConnection() {
    ESP_LOGI(TAG, "Establishing connection...");
    struct sockaddr_in dest_addr;
    dest_addr.sin_addr.s_addr = inet_addr(CONFIG_SERVER_IP);
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(CONFIG_SERVER_PORT);

    global_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (global_sock < 0) {
        ESP_LOGE(TAG, "Unable to create socket.");
        return false;
    }

    if (connect(global_sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr)) != 0) {
        ESP_LOGE(TAG, "Socket connection failed.");
        close(global_sock);
        global_sock = -1;
        return false;
    }

    ESP_LOGI(TAG, "Socket connected.");
    return true;
}

int iSendMetrics(const char *metrics) {
    if (global_sock < 0 && !bEstablishConnection()) {
        ESP_LOGE(TAG, "Failed to establish connection.");
        return -1;
    }

    int sent_bytes = send(global_sock, metrics, strlen(metrics), 0);
    if (sent_bytes < 0) {
        ESP_LOGE(TAG, "Failed to send metrics.");
        close(global_sock);
        global_sock = -1;
        return -1;
    }

    ESP_LOGI(TAG, "Metrics sent: %s", metrics);
    return sent_bytes;
}

void vSocketTask(void *pvParameters) {
    ESP_LOGI(TAG, "Starting socket task...");
    char buffer[256];

    while (1) {
        if (xQueueReceive(socket_queue, buffer, pdMS_TO_TICKS(10000)) == pdTRUE) {
            if (iSendMetrics(buffer) < 0) {
                ESP_LOGE(TAG, "Failed to send data. Reattempting...");
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
