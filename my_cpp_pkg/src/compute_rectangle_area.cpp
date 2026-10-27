#include "rclcpp/rclcpp.hpp"
#include "my_robot_interfaces/srv/compute_rectangle_area.hpp"

using namespace std::placeholders;

class ComputeRectangleAreaNode : public rclcpp::Node
{
public:
    ComputeRectangleAreaNode() : Node("compute_rectangle_area")
    {
        // Bind the service callback using std::placeholders for request and response
        compute_area_service_ = this->create_service<my_robot_interfaces::srv::ComputeRectangleArea>(
            "compute_rectangle_area",
            std::bind(&ComputeRectangleAreaNode::computeRectangleArea, this, _1, _2));

        RCLCPP_INFO(this->get_logger(), "Compute rectangle area service has been started.");
    }

private:
    // Correct ROS 2 service callback signature
    void computeRectangleArea(
        const std::shared_ptr<my_robot_interfaces::srv::ComputeRectangleArea::Request> request,
        const std::shared_ptr<my_robot_interfaces::srv::ComputeRectangleArea::Response> response)
    {
        response->area = request->length * request->width;
        RCLCPP_INFO(this->get_logger(), "Incoming request: length=%.2f, width=%.2f -> Area: %.2f",
                    request->length, request->width, response->area);
    }

    // Declare member variable inside the class scope
    rclcpp::Service<my_robot_interfaces::srv::ComputeRectangleArea>::SharedPtr compute_area_service_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ComputeRectangleAreaNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}