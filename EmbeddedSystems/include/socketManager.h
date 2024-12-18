#ifndef SOCKET_MANAGER_H
#define SOCKET_MANAGER_H

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

bool bEstablishConnection(void);
int iSendMetrics(const char *metrics);
void vSocketTask(void *pvParameters);
int iCreateProtocol(const char *metrics, char **out_buffer);

extern int global_sock;  // Global socket variable for shared access.
extern QueueHandle_t socket_queue;

#endif // SOCKET_MANAGER_H
