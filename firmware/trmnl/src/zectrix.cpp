#include "zectrix.h"

#ifdef BOARD_ZECTRIX

#include <Arduino.h>
#include <DEV_Config.h>
#include <driver/gpio.h>
#include <driver/rtc_io.h>
#include <esp_timer.h>
#include <power.h>

namespace {

  // Status LED (GPIO3, active-low): blinks for the whole awake period (WiFi connect,
  // fetch, panel refresh) so a wake is visible; see zectrix_prepare_deep_sleep() for sleep.
  constexpr uint64_t LED_BLINK_HALF_PERIOD_US = 250 * 1000; // 250 ms on / 250 ms off
  esp_timer_handle_t led_blink_timer = nullptr;
  bool led_on = false;

  void led_blink_tick(void *) {
    led_on = !led_on;
    gpio_set_level(static_cast<gpio_num_t>(ZECTRIX_LED_PIN), led_on ? 0 : 1);
  }

  void start_led_blink() {
    esp_timer_create_args_t args = {};
    args.callback = &led_blink_tick;
    args.name = "led_blink";
    if (esp_timer_create(&args, &led_blink_timer) == ESP_OK) {
      esp_timer_start_periodic(led_blink_timer, LED_BLINK_HALF_PERIOD_US);
    }
  }

  void stop_led_blink() {
    if (led_blink_timer == nullptr) return;
    esp_timer_stop(led_blink_timer);
    esp_timer_delete(led_blink_timer);
    led_blink_timer = nullptr;
  }

  void configure_output(gpio_num_t pin, uint32_t level) {
    rtc_gpio_hold_dis(pin);
    rtc_gpio_deinit(pin);
    pinMode(static_cast<uint8_t>(pin), OUTPUT);
    digitalWrite(static_cast<uint8_t>(pin), level);
  }

  void hold_rtc_output(gpio_num_t pin, uint32_t level) {
    rtc_gpio_hold_dis(pin);
    rtc_gpio_init(pin);
    rtc_gpio_set_direction(pin, RTC_GPIO_MODE_OUTPUT_ONLY);
    rtc_gpio_set_level(pin, level);
    rtc_gpio_hold_en(pin);
  }

} // namespace

void zectrix_power_init() {
  gpio_deep_sleep_hold_dis();

  configure_output(static_cast<gpio_num_t>(VBAT_HOLD_PIN), HIGH);
  configure_output(static_cast<gpio_num_t>(EPD_POWER_PIN), HIGH);
  // Nothing else drives the status LED; a floating GPIO3 lets it glow. Keep it off.
  configure_output(static_cast<gpio_num_t>(ZECTRIX_LED_PIN), HIGH);
  start_led_blink();
  delay(10);
}

void zectrix_prepare_deep_sleep() {
  // The panel is bistable, so its power rail can be disabled after refresh.
  hold_rtc_output(static_cast<gpio_num_t>(EPD_POWER_PIN), LOW);

  // GPIO17 controls the board's battery power latch. Letting it fall LOW cuts
  // power to the ESP32-S3 and prevents timer/button deep-sleep wake-up.
  hold_rtc_output(static_cast<gpio_num_t>(VBAT_HOLD_PIN), HIGH);

  // Status LED (active-low) during sleep: solid on while charging over USB (power is free
  // then), off when fully charged or on battery so it never drains the battery. The charger
  // state is re-read on every wake, so the LED catches up within one refresh interval.
  stop_led_blink();
  bool charging = power().chargingStatus() == ChargingStatus::CHARGING;
  hold_rtc_output(static_cast<gpio_num_t>(ZECTRIX_LED_PIN), charging ? LOW : HIGH);
  gpio_deep_sleep_hold_en();
}

#endif
