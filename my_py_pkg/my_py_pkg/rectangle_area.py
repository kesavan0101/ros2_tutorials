#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from my_robot_interfaces.srv import ComputeRectangleArea


class RectangleAreaNode(Node): 
    def __init__(self):
        super().__init__("rectangle_area_node") 
        self.srv_ = self.create_service(ComputeRectangleArea, "compute_rectangle_area", self.compute_rectangle_area_callback)
        self.get_logger().info("Rectangle Area Service has been started.")

    def compute_rectangle_area_callback(self, request, response):
        response.area = request.length * request.width
        self.get_logger().info(f"Received request: length={request.length}, width={request.width}. Computed area={response.area}.")
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RectangleAreaNode() 
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
