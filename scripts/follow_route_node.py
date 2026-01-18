#!/usr/bin/env python3

import rclpy
from rclpy.parameter import Parameter
from route_navigator import RobotRouteNavigator, RunningTask, TaskResult
import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException
from rclpy.node import Node

def wait_for_transform(node: Node, target_frame: str, source_frame: str, timeout_sec=10.0):
    tf_buffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tf_buffer, node)
    node.get_logger().info(f'Waiting for TF {source_frame} -> {target_frame}...')
    start_time = node.get_clock().now()

    while rclpy.ok():
        try:
            # request latest transform
            tf_buffer.lookup_transform(target_frame, source_frame, rclpy.time.Time())
            return True
        except (LookupException, ConnectivityException, ExtrapolationException):
            pass
        if (node.get_clock().now() - start_time).nanoseconds * 1e-9 > timeout_sec:
            node.get_logger().error(f'TF {source_frame} -> {target_frame} not available after {timeout_sec}s')
            return False
        rclpy.spin_once(node, timeout_sec=0.1)

def main():
    rclpy.init()
    navigator = RobotRouteNavigator()

    # Route Navigator parameters
    navigator.declare_parameter('start_node', 0)
    navigator.declare_parameter('goal_node', 1)
    start_node = navigator.get_parameter('start_node').value
    goal_node = navigator.get_parameter('goal_node').value

    navigator.get_logger().info(f'Starting Route Navigator | start_node={start_node} goal_node={goal_node}')

    # Wait for TF map->base_footprint before executing route
    if not wait_for_transform(navigator, 'map', 'base_link'):
        navigator.get_logger().error('Required TF not available, exiting')
        rclpy.shutdown()
        return

    route_task = navigator.computeAndTrackRoute(start_node, goal_node)
    if route_task is None:
        navigator.get_logger().error('Failed to start route execution')
        rclpy.shutdown()
        return

    follow_path_task = RunningTask.NONE
    last_feedback = None

    while rclpy.ok() and not navigator.isTaskComplete(route_task):
        feedback = navigator.getFeedback()
        while feedback:
            if last_feedback is None or feedback.last_node_id != last_feedback.last_node_id:
                navigator.get_logger().info(f'Route progress: node {feedback.last_node_id} → {feedback.next_node_id}')
            if feedback.rerouted or follow_path_task == RunningTask.NONE:
                navigator.get_logger().info('New path received, sending to controller')
                follow_path_task = navigator.followPath(feedback.path)
            last_feedback = feedback
            feedback = navigator.getFeedback()
        rclpy.spin_once(navigator, timeout_sec=0.1)

    result = navigator.getResult()
    navigator.get_logger().info(f'Route navigation result: {result.name}')

    navigator.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
