#ifndef TIME_MANAGER_H
#define TIME_MANAGER_H

#include <time.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_sntp.h"
#include "driver/gptimer.h"

#define TIMER_PERIOD_MS  5000 // How often for the hardware timer to trigger

// Define the example_queue_element_t type
typedef struct {
    uint32_t event_count;
} example_queue_element_t;

extern gptimer_handle_t gptimer;
extern QueueHandle_t metrics_queue;


// Function to initialize SNTP (assumes implementation is available elsewhere)
void vSntpInit(void);

// Function to obtain and synchronize the system time using NTP
void vObtainTime(void);

void vGptimerInit(void);

bool IRAM_ATTR bGptimerCallback(gptimer_handle_t timer, const gptimer_alarm_event_data_t *edata, void *user_data);

#endif // TIME_MANAGER_H
