#!/usr/bin/env python3
from pexpect import which

import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts

def main(args=None):
    rclpy.init(args=args)
    node = Node("add_two_ints_client_no_oop") 

    client = node.create_client(AddTwoInts, "add_two_ints")
    while not client.wait_for_service(timeout_sec=1.0):     #we create a client and wait for the service to be available 
        node.get_logger().warn("Waiting for AddTwoInts service...")

    request = AddTwoInts.Request() #we create a request object and set the values of a and b to 3 and 8, respectively
    request.a = 3
    request.b = 8

    future = client.call_async(request) #we send that request
    rclpy.spin_until_future_complete(node, future) #we make the node spin until the future is complete, 
                                                   #which means that we wait for the response from the service
    response = future.result()
    node.get_logger().info(str(request.a) + " + " +
                           str(request.b) + " = " + str(response.sum))

    rclpy.shutdown()


if __name__ == "__main__":
    main()
