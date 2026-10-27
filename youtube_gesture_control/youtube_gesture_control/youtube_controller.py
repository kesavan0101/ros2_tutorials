#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import pyautogui
from youtube_gesture_interfaces.msg import GestureCommand

class YouTubeControllerNode(Node):
    def __init__(self):
        super().__init__('youtube_controller')
        
        self.subscription = self.create_subscription(
            GestureCommand,
            '/detected_gesture',
            self.gesture_callback,
            10
        )
        
        pyautogui.FAILSAFE = False
        self.get_logger().info('YouTube Controller Node active (Dual Hand + Fullscreen).')

    def gesture_callback(self, msg):
        gesture = msg.gesture_type
        side = msg.hand_side

        # Right Hand: 'k' toggles Play/Pause
        if gesture == "PALM_SHOW":
            pyautogui.press('k')
            self.get_logger().info('Action: Toggled YouTube Play/Pause (Pressed "k")')

        # Left Hand: 'f' toggles Fullscreen
        elif gesture == "FULLSCREEN":
            pyautogui.press('f')
            self.get_logger().info('Action: Toggled YouTube Fullscreen (Pressed "f")')
            
        # Mute/Unmute
        elif gesture == "MUTE" or gesture == "FIST_CLOSED":
            pyautogui.press('m')  
            self.get_logger().info('Action: Toggled YouTube Mute (Pressed "m")')

        # Seek Forward (+5s)
        elif gesture == "SEEK_FORWARD":
            pyautogui.press('right')  
            self.get_logger().info(f'[{side.upper()}] Action: Skipped Forward +5s (Right Arrow)')

        # Seek Backward (-5s)
        elif gesture == "SEEK_BACKWARD":
           pyautogui.press('left')   
           self.get_logger().info(f'[{side.upper()}] Action: Skipped Backward -5s (Left Arrow)')        

def main(args=None):
    rclpy.init(args=args)
    node = YouTubeControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()