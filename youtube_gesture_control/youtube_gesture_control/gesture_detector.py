#!/usr/bin/env python3
import time
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from youtube_gesture_interfaces.msg import GestureCommand


class MediaPipeGestureNode(Node):
    def __init__(self):
        super().__init__("gesture_detector")

        # ROS Communication Setup
        self.sub_image = self.create_subscription(
            Image, "/image_raw", self.image_callback, 10
        )
        self.pub_gesture = self.create_publisher(
            GestureCommand, "/detected_gesture", 10
        )
        self.bridge = CvBridge()

        # MediaPipe Task Configuration
        base_options = python.BaseOptions(model_asset_path="hand_landmarker.task")
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

        # Independent state tracker for each hand
        self.hands_data = {
            "right": self._create_hand_state_template(),
            "left": self._create_hand_state_template()
        }

        self.get_logger().info("MediaPipe Gesture Detector Initialized with GUI Active.")

    @staticmethod
    def _create_hand_state_template():
        return {
            "state": None,
            "initialized": False,
            "point_start_time": None,
            "action_triggered": False,
            "last_continuous_action_time": 0.0,
            "current_seek_is_forward": True,
            "accumulated_skip_seconds": 5
        }

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"CvBridge error: {e}")
            return

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        recognition_result = self.landmarker.detect(mp_image)

        annotated_frame = frame.copy()
        detected_hands = set()
        current_time = time.time()
        transitions = {}

        if recognition_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(recognition_result.hand_landmarks):
                raw_handedness = recognition_result.handedness[idx][0].category_name.lower()
                handedness = "right" if raw_handedness == "left" else "left"
                detected_hands.add(handedness)

                self.draw_hand_landmarks(annotated_frame, hand_landmarks, w, h)
                h_data = self.hands_data[handedness]

                # 1. Process Pointing Gesture (Seek / Scrubbing)
                is_pointing, is_palm_facing = self.check_pointing_gesture(hand_landmarks, handedness)

                if is_pointing:
                    h_data["initialized"] = False  # Reset pose state while pointing

                    if h_data["point_start_time"] is None:
                        h_data["point_start_time"] = current_time
                        h_data["action_triggered"] = False
                        h_data["current_seek_is_forward"] = is_palm_facing
                        h_data["accumulated_skip_seconds"] = 5

                    elapsed = current_time - h_data["point_start_time"]

                    # Initial 2-second hold trigger
                    if elapsed >= 2.0 and not h_data["action_triggered"]:
                        direction = "SEEK_FORWARD" if h_data["current_seek_is_forward"] else "SEEK_BACKWARD"
                        self.publish_gesture(handedness, direction)
                        self.get_logger().info(f"[{handedness.upper()}] Point Held 2s -> {direction}")
                        
                        h_data["action_triggered"] = True
                        h_data["last_continuous_action_time"] = current_time

                    # Continuous scrubbing after 4 seconds (every 1 second)
                    elif elapsed >= 4.0 and h_data["action_triggered"]:
                        if current_time - h_data["last_continuous_action_time"] >= 1.0:
                            h_data["accumulated_skip_seconds"] += 5
                            direction = "SEEK_FORWARD" if h_data["current_seek_is_forward"] else "SEEK_BACKWARD"
                            self.publish_gesture(handedness, direction)
                            
                            self.get_logger().info(
                                f"[{handedness.upper()}] Continuous Scrub -> {direction} "
                                f"(±{h_data['accumulated_skip_seconds']}s)"
                            )
                            h_data["last_continuous_action_time"] = current_time

                    self._render_text_overlay(annotated_frame, handedness, is_pointing=True, elapsed=elapsed, h_data=h_data)

                # 2. Process Pose Transitions (Play/Pause, Fullscreen, Mute)
                else:
                    self.reset_pointing_state(handedness)
                    detected_pose_state = self.classify_pose_state(hand_landmarks, handedness)

                    if not h_data["initialized"]:
                        h_data["state"] = detected_pose_state
                        h_data["initialized"] = True
                    else:
                        prev_state = h_data["state"]
                        if prev_state == 1 and detected_pose_state == 2:
                            transitions[handedness] = "1->2"
                        elif prev_state == 4 and detected_pose_state == 3:
                            transitions[handedness] = "4->3"

                        h_data["state"] = detected_pose_state

                    self._render_text_overlay(annotated_frame, handedness, is_pointing=False, h_data=h_data)

        # 3. Evaluate Cross-Hand Transitions and Dispatch Commands
        self._evaluate_and_dispatch_transitions(transitions)

        # Clean up tracking state for hands missing from frame
        for side in ["right", "left"]:
            if side not in detected_hands:
                self.reset_pointing_state(side)
                self.hands_data[side]["state"] = None
                self.hands_data[side]["initialized"] = False

        # Display window (GUI active)
        cv2.imshow("MediaPipe Dual Hand Control", annotated_frame)
        cv2.waitKey(1)

    def _evaluate_and_dispatch_transitions(self, transitions):
        right_trans = transitions.get("right")
        left_trans = transitions.get("left")

        if right_trans == "1->2" and left_trans == "1->2":
            self.publish_gesture("both", "FULLSCREEN")
            self.get_logger().info("[BOTH HANDS] Transition 1 -> 2: FULLSCREEN")
        elif right_trans == "1->2":
            self.publish_gesture("right", "PALM_SHOW")
            self.get_logger().info("[RIGHT] Transition 1 -> 2: PLAY/PAUSE")
        elif left_trans == "1->2":
            self.publish_gesture("left", "FULLSCREEN")
            self.get_logger().info("[LEFT] Transition 1 -> 2: FULLSCREEN")

        if right_trans == "4->3":
            self.publish_gesture("right", "MUTE")
            self.get_logger().info("[RIGHT] Transition 4 -> 3: MUTE")
        if left_trans == "4->3":
            self.publish_gesture("left", "MUTE")
            self.get_logger().info("[LEFT] Transition 4 -> 3: MUTE")

    def _render_text_overlay(self, frame, handedness, is_pointing, h_data=None, elapsed=0.0):
        text_y = 50 if handedness == "right" else 110
        if is_pointing:
            skip_amt = h_data["accumulated_skip_seconds"] if h_data["action_triggered"] else 5
            dir_char = "+" if h_data["current_seek_is_forward"] else "-"
            text = f"{handedness.upper()} Point: {elapsed:.1f}s ({dir_char}{skip_amt}s)"
            color = (0, 255, 255)
        else:
            text = f"{handedness.upper()} State: {h_data['state']}"
            color = (0, 255, 0)

        cv2.putText(frame, text, (20, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def classify_pose_state(self, landmarks, handedness):
        tips = [landmarks[8], landmarks[12], landmarks[16], landmarks[20]]
        pips = [landmarks[6], landmarks[10], landmarks[14], landmarks[18]]
        extended = sum(1 for tip, pip in zip(tips, pips) if tip.y < pip.y - 0.02)
        is_open = extended >= 3

        thumb_mcp_x = landmarks[2].x
        pinky_mcp_x = landmarks[17].x
        is_palm_facing = (thumb_mcp_x < pinky_mcp_x) if handedness == "right" else (thumb_mcp_x > pinky_mcp_x)

        if is_palm_facing:
            return 2 if is_open else 1
        else:
            return 4 if is_open else 3

    def check_pointing_gesture(self, landmarks, handedness):
        index_extended = landmarks[8].y < landmarks[6].y - 0.02
        middle_curled = landmarks[12].y > landmarks[10].y
        ring_curled = landmarks[16].y > landmarks[14].y
        pinky_curled = landmarks[20].y > landmarks[18].y
        is_pointing = index_extended and middle_curled and ring_curled and pinky_curled

        thumb_mcp_x = landmarks[2].x
        pinky_mcp_x = landmarks[17].x
        is_palm_facing = (thumb_mcp_x < pinky_mcp_x) if handedness == "right" else (thumb_mcp_x > pinky_mcp_x)

        return is_pointing, is_palm_facing

    def reset_pointing_state(self, handedness):
        self.hands_data[handedness]["point_start_time"] = None
        self.hands_data[handedness]["action_triggered"] = False
        self.hands_data[handedness]["accumulated_skip_seconds"] = 5

    def draw_hand_landmarks(self, img, landmarks, w, h):
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (5, 9), (9, 10), (10, 11), (11, 12),
            (9, 13), (13, 14), (14, 15), (15, 16),
            (13, 17), (17, 18), (18, 19), (19, 20),
            (0, 17)
        ]

        for start, end in connections:
            cv2.line(img, pts[start], pts[end], (0, 255, 0), 2)

        for i, pt in enumerate(pts):
            color = (0, 0, 255) if i in [4, 8, 12, 16, 20] else (255, 0, 0)
            cv2.circle(img, pt, 5, color, -1)

    def publish_gesture(self, hand_side, gesture_type):
        cmd = GestureCommand()
        cmd.hand_side = hand_side
        cmd.gesture_type = gesture_type
        cmd.confidence = 0.95
        cmd.pinch_distance = 0.0
        self.pub_gesture.publish(cmd)

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MediaPipeGestureNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()