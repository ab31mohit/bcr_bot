#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Header
from rclpy.parameter import Parameter

from route_navigator import (RobotRouteNavigator, RunningTask, TaskResult)

def make_pose(x: float, y: float, yaw_w: float = 1.0) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.w = yaw_w
    return pose


def main() -> None:
    rclpy.init()

    navigator = RobotRouteNavigator()

    # ------------------------------------------------------------
    # 1. Wait for Nav2 (route + controller) to become ACTIVE
    # ------------------------------------------------------------
    if not navigator.waitUntilNav2Active():
        navigator.get_logger().error('Nav2 route stack not available, exiting')
        rclpy.shutdown()
        return

    # ------------------------------------------------------------
    # 2. Set initial pose (must match map frame)
    # ------------------------------------------------------------
    initial_pose = make_pose(7.5, 7.5)
    initial_pose.header.stamp = navigator.get_clock().now().to_msg()

    navigator.get_logger().info(
        f'Setting initial pose: ({initial_pose.pose.position.x}, '
        f'{initial_pose.pose.position.y})'
    )

    # IMPORTANT:
    # Route-based navigation assumes localization is already running (AMCL)
    # Initial pose should be published BEFORE route execution
    navigator.set_parameters([
        Parameter('use_sim_time', Parameter.Type.BOOL, True)
    ])


    # ------------------------------------------------------------
    # 3. Define goal (pose-based or node-id based)
    # ------------------------------------------------------------
    goal_pose = make_pose(20.12, 11.83)
    goal_pose.header.stamp = navigator.get_clock().now().to_msg()

    # ------------------------------------------------------------
    # 4. Compute & track route
    # ------------------------------------------------------------
    navigator.get_logger().info('Requesting ComputeAndTrackRoute...')
    route_task = navigator.computeAndTrackRoute(initial_pose, goal_pose)

    if route_task is None:
        navigator.get_logger().error('Failed to start route tracking')
        rclpy.shutdown()
        return

    follow_path_task = RunningTask.NONE
    last_feedback = None
    task_canceled = False

    # ------------------------------------------------------------
    # 5. Route tracking loop
    # ------------------------------------------------------------
    while rclpy.ok() and not navigator.isTaskComplete(route_task):

        feedback = navigator.getFeedback()
        while feedback is not None:

            # Log node-to-node progress
            if (not last_feedback or
                feedback.last_node_id != last_feedback.last_node_id or
                feedback.next_node_id != last_feedback.next_node_id):

                navigator.get_logger().info(
                    f'Route progress: node {feedback.last_node_id} → '
                    f'{feedback.next_node_id} (edge {feedback.current_edge_id})'
                )

            # Handle rerouting or first-time path publication
            if feedback.rerouted or follow_path_task == RunningTask.NONE:
                navigator.get_logger().info(
                    'New path received from route_server, sending to controller'
                )
                follow_path_task = navigator.followPath(feedback.path)

                if follow_path_task is None:
                    navigator.get_logger().error('Controller rejected path')
                    navigator.cancel()
                    task_canceled = True
                    break

            last_feedback = feedback
            feedback = navigator.getFeedback()

        # --------------------------------------------------------
        # 6. Monitor controller execution
        # --------------------------------------------------------
        if follow_path_task != RunningTask.NONE and \
           navigator.isTaskComplete(follow_path_task):

            navigator.get_logger().warn(
                'Controller task completed before route finished'
            )
            navigator.cancel()
            task_canceled = True
            break

        rclpy.spin_once(navigator, timeout_sec=0.1)

    # ------------------------------------------------------------
    # 7. Wait for controller to fully finish
    # ------------------------------------------------------------
    while (rclpy.ok() and
           follow_path_task != RunningTask.NONE and
           not navigator.isTaskComplete(follow_path_task) and
           not task_canceled):
        rclpy.spin_once(navigator, timeout_sec=0.1)

    # ------------------------------------------------------------
    # 8. Final result handling
    # ------------------------------------------------------------
    result = navigator.getResult()

    if result == TaskResult.SUCCEEDED:
        navigator.get_logger().info('Route navigation SUCCEEDED')
    elif result == TaskResult.CANCELED:
        navigator.get_logger().warn('Route navigation CANCELED')
    elif result == TaskResult.FAILED:
        navigator.get_logger().error('Route navigation FAILED')
    else:
        navigator.get_logger().error('Route navigation returned UNKNOWN state')

    navigator.get_logger().info('Shutting down route navigator')
    navigator.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
