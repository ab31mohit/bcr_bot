#! /usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, QoSDurabilityPolicy
from geometry_msgs.msg import Twist

class CmdVelRemapper(Node):
    def __init__(self):
        super().__init__('cmd_vel_remapper')

        # ----------------------------
        # Declare parameters
        # ----------------------------
        self.declare_parameter('cmd_vel_topic_in', 'cmd_vel_collision')
        self.declare_parameter('cmd_vel_topic_out', '/bcr_bot/cmd_vel')

        input_topic = self.get_parameter(
            'cmd_vel_topic_in').get_parameter_value().string_value
        output_topic = self.get_parameter(
            'cmd_vel_topic_out').get_parameter_value().string_value

        self.get_logger().info(f"Subscribing to: {input_topic}")
        self.get_logger().info(f"Publishing to:  {output_topic}")

        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.VOLATILE,
            depth=10
        )

        # Subscriber
        self.subscription = self.create_subscription(
            Twist,
            input_topic,
            self.cmd_vel_callback,
            qos_profile
        )
        self.subscription  # Prevent unused variable warning

        # Publisher
        self.publisher = self.create_publisher(
            Twist,
            output_topic,
            qos_profile
        )

    def cmd_vel_callback(self, msg):
        # Republish the received message to output topic (/bcr_bot/cmd_vel)
        self.publisher.publish(msg)


def main(args=None):
    
    rclpy.init(args=args)
    node = CmdVelRemapper()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
