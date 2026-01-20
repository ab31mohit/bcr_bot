#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

from route_navigator import RobotRouteNavigator, RunningTask, TaskResult


def wait_for_transform(node: Node, target_frame: str, source_frame: str, timeout_sec=10.0):
    tf_buffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tf_buffer, node)
    node.get_logger().info(f'Waiting for TF {source_frame} -> {target_frame}...')
    start_time = node.get_clock().now()

    while rclpy.ok():
        try:
            tf_buffer.lookup_transform(target_frame, source_frame, rclpy.time.Time())
            return True
        except (LookupException, ConnectivityException, ExtrapolationException):
            pass

        if (node.get_clock().now() - start_time).nanoseconds * 1e-9 > timeout_sec:
            node.get_logger().error('TF timeout')
            return False

        rclpy.spin_once(node, timeout_sec=0.1)


def build_inspection_sequence(start_node, loop_nodes, loop_count, return_node):
    seq = [start_node]
    for _ in range(loop_count):
        seq.extend(loop_nodes)
    seq.append(return_node)
    return seq


def execute_node_segment(navigator, start_node, goal_node):
    navigator.get_logger().info(f'Executing segment: {start_node} → {goal_node}')

    route_task = navigator.computeAndTrackRoute(start_node, goal_node)
    if route_task is None:
        navigator.get_logger().error('Failed to start route task')
        return False

    follow_path_task = RunningTask.NONE
    last_feedback = None

    while rclpy.ok() and not navigator.isTaskComplete(route_task):
        feedback = navigator.getFeedback()
        while feedback:
            if last_feedback is None or feedback.last_node_id != last_feedback.last_node_id:
                navigator.get_logger().info(
                    f'Route progress: node {feedback.last_node_id} → {feedback.next_node_id}'
                )

            if feedback.rerouted or follow_path_task == RunningTask.NONE:
                navigator.get_logger().info('New path received')
                follow_path_task = navigator.followPath(feedback.path)

            last_feedback = feedback
            feedback = navigator.getFeedback()

        rclpy.spin_once(navigator, timeout_sec=0.1)

    result = navigator.getResult()
    navigator.get_logger().info(f'Segment result: {result.name}')
    return result.name == 'SUCCEEDED'


def main():
    rclpy.init()
    navigator = RobotRouteNavigator()

    if not wait_for_transform(navigator, 'map', 'base_link'):
        rclpy.shutdown()
        return

    # ===================== USER INPUT =====================
    start_node = 0
    loop_nodes = [2, 3, 4, 6]
    loop_count = 2
    return_node = 0
    # ======================================================

    node_sequence = build_inspection_sequence(
        start_node, loop_nodes, loop_count, return_node
    )

    navigator.get_logger().info(f'Node sequence: {start_node} -> {loop_nodes} ({loop_count} loops) -> {return_node}')

    for i in range(len(node_sequence) - 1):
        success = execute_node_segment(
            navigator,
            node_sequence[i],
            node_sequence[i + 1]
        )

        if not success:
            navigator.get_logger().error('Inspection sequence aborted due to failure!')
            break

    navigator.get_logger().info('Inspection mission completed!')
    navigator.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
