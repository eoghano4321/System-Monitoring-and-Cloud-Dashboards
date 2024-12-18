#ifndef DATA_COLLECTOR_H
#define DATA_COLLECTOR_H

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include <time.h>
#include "timeManager.h"

// Macro definitions
#ifndef MAX_DATA_LEN
#define MAX_DATA_LEN 256  // Maximum length for data buffer
#endif

// External queue handles (declared in other modules, like main.c)
extern QueueHandle_t metrics_queue;
extern QueueHandle_t socket_queue;

// External variables (defined in other modules, like gpioManager.c)
extern int alarming;  // Indicates if an alarm is active

// Function prototypes
void vDataCollectionTask(void *pvParameters);  // Task for data collection

#endif // DATA_COLLECTOR_H
