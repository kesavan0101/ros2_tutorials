#!/usr/bin/env python3
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class CameraDriverNode(Node):
    def __init__(self):
        super().__init__("camera_driver_node")

        self.publisher_ = self.create_publisher(Image, "/image_raw", 10)
        self.bridge = CvBridge()

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not self.cap.isOpened():
            self.get_logger().error("Could not open video device /dev/video0")

        self.timer = self.create_timer(1.0 / 30.0, self.timer_callback)
        self.get_logger().info("Webcam node initialized and publishing at 30 FPS.")

    def timer_callback(self):
        ret, frame = self.cap.read()

        if not ret or frame is None or frame.size == 0:
            self.get_logger().warn("Failed to capture valid frame from webcam.")
            return

        # Explicitly enforce uint8 contiguous memory layout for ROS 2 cv_bridge
        frame = np.ascontiguousarray(frame, dtype=np.uint8)

        try:
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            self.publisher_.publish(msg)
        except Exception as e:
            self.get_logger().error(f"cv_bridge error: {e}")

    def destroy_node(self):
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraDriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()