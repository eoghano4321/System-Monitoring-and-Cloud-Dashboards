#ifndef GPIO_MANAGER_H
#define GPIO_MANAGER_H

void vGpioInit(void);
void vToggleAlarm(int level);
extern int alarming;

#endif // GPIO_MANAGER_H
