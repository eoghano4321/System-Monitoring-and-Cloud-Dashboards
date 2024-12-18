#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/adc.h"
#include "esp_log.h"

// Macro definitions
#ifndef GAS_THRESHOLD
#define GAS_THRESHOLD 4000  // Default threshold for gas level
#endif

// External queue handle (declared in other modules, like main.c)
extern QueueHandle_t alarm_queue;

int iReadGasSensor(void);

void vSensorPollingTask(void *pvParameters);

#endif // SENSOR_MANAGER_H
