import unittest

from smart_scan.core import HandStatus, Observation, ScanController, State


CONFIG = {
    "turn_threshold_percent": 2.5,
    "quiet_threshold_percent": 0.8,
    "scene_change_percent": 3.0,
    "debounce_seconds": 0.8,
    "cooldown_seconds": 1.8,
}


class ScanControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = ScanController(CONFIG)

    def start_change(self):
        self.assertEqual(self.controller.update(Observation(5, 12, HandStatus.CLEAR), 0).state,
                         State.MOVING)
        self.assertEqual(self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.1).state,
                         State.SETTLING)

    def test_static_hand_in_allowed_zone_can_trigger(self):
        self.start_change()
        self.controller.update(Observation(0.2, 12, HandStatus.ALLOWED), 0.2)
        self.assertFalse(self.controller.update(Observation(0.2, 12, HandStatus.ALLOWED), 0.9).trigger)
        self.assertTrue(self.controller.update(Observation(0.2, 12, HandStatus.ALLOWED), 1.01).trigger)

    def test_hand_in_content_blocks_until_stable_clear(self):
        self.start_change()
        self.assertEqual(self.controller.update(Observation(0.2, 12, HandStatus.BLOCKED), 0.2).state,
                         State.BLOCKED)
        self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.5)
        self.assertFalse(self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 1.0).trigger)
        self.assertTrue(self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 1.31).trigger)

    def test_motion_or_invalid_frame_resets_timer(self):
        self.start_change()
        self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.2)
        self.assertEqual(self.controller.update(Observation(1.0, 12, HandStatus.CLEAR), 0.7).state,
                         State.MOVING)
        self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.8)
        self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.9)
        self.assertEqual(self.controller.update(Observation(0, 12, HandStatus.UNKNOWN, False), 1.5).state,
                         State.WAIT_CAMERA)
        self.assertEqual(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.6).state,
                         State.IDLE)
        self.assertFalse(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.7).trigger)

    def test_missing_scan_area_restarts_stability_timer_on_recovery(self):
        self.start_change()
        self.controller.update(Observation(0.2, 12, HandStatus.CLEAR), 0.2)
        missing = Observation(0, 0, HandStatus.UNKNOWN, True, False)
        self.assertEqual(self.controller.update(missing, 1.5).state, State.WAIT_AREA)
        self.assertEqual(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.6).state,
                         State.SETTLING)
        self.assertFalse(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.7).trigger)
        self.assertFalse(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 2.3).trigger)
        self.assertTrue(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 2.41).trigger)

    def test_missing_scan_area_without_page_change_stays_ready(self):
        unchanged = Observation(0, 0, HandStatus.CLEAR)
        missing = Observation(0, 0, HandStatus.UNKNOWN, True, False)
        self.assertEqual(self.controller.update(missing, 0).state, State.WAIT_AREA)
        self.assertEqual(self.controller.update(unchanged, 0.1).state, State.IDLE)
        self.assertFalse(self.controller.update(unchanged, 1).trigger)

    def test_changed_page_can_settle_when_motion_was_missed(self):
        changed = Observation(0, 12, HandStatus.ALLOWED)
        self.assertEqual(self.controller.update(changed, 0).state, State.SETTLING)
        self.assertFalse(self.controller.update(changed, 0.7).trigger)
        self.assertTrue(self.controller.update(changed, 0.81).trigger)

    def test_scene_only_change_still_respects_hand_block(self):
        changed = Observation(0, 12, HandStatus.BLOCKED)
        self.assertEqual(self.controller.update(changed, 0).state, State.SETTLING)
        self.assertEqual(self.controller.update(changed, 0.1).state, State.BLOCKED)
        self.assertFalse(self.controller.update(changed, 1.0).trigger)

    def test_uncertain_finger_can_clear_without_a_new_page_turn(self):
        self.start_change()
        self.assertEqual(self.controller.update(Observation(0, 12, HandStatus.UNKNOWN), 0.2).state,
                         State.UNCERTAIN)
        self.controller.update(Observation(0, 12, HandStatus.ALLOWED), 0.6)
        self.assertTrue(self.controller.update(Observation(0, 12, HandStatus.ALLOWED), 1.41).trigger)

    def test_hand_motion_without_scene_change_does_not_scan(self):
        self.assertEqual(self.controller.update(Observation(5, 1, HandStatus.ALLOWED), 0).state,
                         State.IDLE)

    def test_pause_resumes_to_idle(self):
        self.start_change()
        self.controller.toggle_pause()
        self.assertEqual(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1).state,
                         State.PAUSED)
        self.controller.toggle_pause()
        self.assertEqual(self.controller.update(Observation(0, 0, HandStatus.CLEAR), 2).state,
                         State.IDLE)

    def test_cooldown_prevents_repeat_scan(self):
        self.start_change()
        self.controller.update(Observation(0, 12, HandStatus.CLEAR), 0.2)
        self.assertTrue(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.1).trigger)
        self.assertFalse(self.controller.update(Observation(0, 12, HandStatus.CLEAR), 1.2).trigger)

    def test_mode_change_preserves_cooldown_before_initial_scan(self):
        self.controller.manual_trigger(0)
        self.controller.reset_for_mode(0.2)
        changed = Observation(0, 3, HandStatus.CLEAR)
        self.assertEqual(self.controller.update(changed, 0.3).state, State.COOLDOWN)
        self.assertFalse(self.controller.update(changed, 1.7).trigger)
        self.assertEqual(self.controller.update(changed, 1.9).state, State.SETTLING)
        self.assertFalse(self.controller.update(changed, 2.6).trigger)
        self.assertTrue(self.controller.update(changed, 2.71).trigger)

    def test_selection_drag_during_cooldown_does_not_allow_early_scan(self):
        self.controller.manual_trigger(0)
        self.controller.update(Observation(0, 0, HandStatus.UNKNOWN, True, False), 0.1)
        changed = Observation(0, 12, HandStatus.CLEAR)
        self.assertEqual(self.controller.update(changed, 0.2).state, State.COOLDOWN)
        self.assertFalse(self.controller.update(changed, 1.1).trigger)
        self.assertEqual(self.controller.update(changed, 1.9).state, State.SETTLING)


if __name__ == "__main__":
    unittest.main()
