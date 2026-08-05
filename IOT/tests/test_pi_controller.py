import unittest
from unittest.mock import patch, MagicMock
import time

import gateway_controller

class TestPiController(unittest.TestCase):
    def setUp(self):
        gateway_controller.reset_system()

    @patch('gateway_controller.read_switch')
    @patch('time.sleep')
    def test_interruptible_sleep_always_true(self, mock_sleep, mock_read_switch):
        # If switch is always ON, interruptible_sleep should return True
        mock_read_switch.return_value = True
        res = gateway_controller.interruptible_sleep(0.5)
        self.assertTrue(res)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch('gateway_controller.read_switch')
    @patch('time.sleep')
    def test_interruptible_sleep_initially_false(self, mock_sleep, mock_read_switch):
        # If switch is OFF, interruptible_sleep should return False immediately
        mock_read_switch.return_value = False
        res = gateway_controller.interruptible_sleep(0.5)
        self.assertFalse(res)
        self.assertEqual(mock_sleep.call_count, 0)

    @patch('gateway_controller.read_switch')
    @patch('time.sleep')
    def test_interruptible_sleep_interrupted(self, mock_sleep, mock_read_switch):
        # Switch is ON for 2 iterations, then turns OFF
        mock_read_switch.side_effect = [True, True, False]
        res = gateway_controller.interruptible_sleep(0.5)
        self.assertFalse(res)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('requests.post')
    @patch('gateway_controller.set_led')
    @patch('time.sleep')
    def test_send_alert_success(self, mock_sleep, mock_set_led, mock_post):
        # Mock requests.post response for success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"success": True, "dispatched_to": "OBHS Staff"}
        mock_post.return_value = mock_response

        # Set active trip to pass validation
        gateway_controller.trip_number = "TRP-1234"

        gateway_controller.send_alert("A1")

        # Verify green LED is turned ON first, red is turned OFF
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_GREEN_A1, True)
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_RED_A1, False)

        # Verify it sleeps 3 seconds
        mock_sleep.assert_called_with(3)

        # Verify both LEDs are turned OFF after sleep
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_GREEN_A1, False)
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_RED_A1, False)

    @patch('requests.post')
    @patch('gateway_controller.set_led')
    @patch('time.sleep')
    def test_send_alert_failure(self, mock_sleep, mock_set_led, mock_post):
        # Mock requests.post response for failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Set active trip to pass validation
        gateway_controller.trip_number = "TRP-1234"

        gateway_controller.send_alert("A1")

        # Verify red LED is turned ON first, green is turned OFF
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_GREEN_A1, False)
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_RED_A1, True)

        # Verify it sleeps 3 seconds
        mock_sleep.assert_called_with(3)

        # Verify both LEDs are turned OFF after sleep
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_GREEN_A1, False)
        mock_set_led.assert_any_call(gateway_controller.PIN_LED_RED_A1, False)

    @patch('threading.Thread.start')
    def test_button_debounce(self, mock_thread_start):
        # Initial time: 1000.0
        with patch('time.time', return_value=1000.0):
            gateway_controller.handle_a1()
            self.assertEqual(mock_thread_start.call_count, 1)

        # Immediate secondary press (1001.0): Should be debounced/ignored
        with patch('time.time', return_value=1001.0):
            gateway_controller.handle_a1()
            self.assertEqual(mock_thread_start.call_count, 1)

        # Press after debounce interval (1006.0): Should proceed
        with patch('time.time', return_value=1006.0):
            gateway_controller.handle_a1()
            self.assertEqual(mock_thread_start.call_count, 2)

if __name__ == "__main__":
    unittest.main()
