#!/usr/bin/env python3

from enum import Enum
from typing import Optional, Union, List

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from lifecycle_msgs.srv import GetState
from action_msgs.msg import GoalStatus

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from nav2_msgs.msg import Route

from nav2_msgs.action import (
    ComputeRoute,
    ComputeAndTrackRoute,
    FollowPath
)


# ------------------------------------------------------------
# Task state enums (same spirit as Nav2 Simple Commander)
# ------------------------------------------------------------

class TaskResult(Enum):
    UNKNOWN = 0
    SUCCEEDED = 1
    CANCELED = 2
    FAILED = 3


class RunningTask(Enum):
    NONE = 0
    COMPUTE_AND_TRACK_ROUTE = 1
    FOLLOW_PATH = 2


# ------------------------------------------------------------
# RobotRouteNavigator
# ------------------------------------------------------------

class RobotRouteNavigator(Node):
    """
    Route-only navigation helper for Nav2 Humble.
    Works with route_server + controller_server only.
    """

    def __init__(self, node_name='robot_route_navigator'):
        super().__init__(node_name)

        # ---- Action clients ----
        self.compute_route_client = ActionClient(
            self, ComputeRoute, 'compute_route'
        )
        self.compute_and_track_route_client = ActionClient(
            self, ComputeAndTrackRoute, 'compute_and_track_route'
        )
        self.follow_path_client = ActionClient(
            self, FollowPath, 'follow_path'
        )

        # ---- Lifecycle check clients ----
        self._route_state_client = self.create_client(
            GetState, '/route_server/get_state'
        )
        self._controller_state_client = self.create_client(
            GetState, '/controller_server/get_state'
        )

        # ---- Internal state ----
        self._route_goal_handle = None
        self._route_result_future = None
        self._follow_goal_handle = None
        self._follow_result_future = None

        self._route_feedback_queue = []
        self._status = None

        self.get_logger().info('RobotRouteNavigator initialized')

    # ============================================================
    # NAV2 READINESS CHECKS
    # ============================================================

    def waitUntilNav2Active(self, timeout_sec: float = 30.0) -> bool:
        """
        Equivalent to Nav2 Simple Commander readiness checks.
        """

        self.get_logger().info('Waiting for Nav2 route stack to become active...')

        if not self._waitForLifecycleNode(
            self._route_state_client, 'route_server', timeout_sec
        ):
            return False

        if not self._waitForLifecycleNode(
            self._controller_state_client, 'controller_server', timeout_sec
        ):
            return False

        self.get_logger().info('Nav2 route stack is ACTIVE')
        return True

    def _waitForLifecycleNode(self, client, name, timeout):
        start_time = self.get_clock().now()

        while not client.wait_for_service(timeout_sec=1.0):
            if (self.get_clock().now() - start_time).nanoseconds * 1e-9 > timeout:
                self.get_logger().error(f'{name} lifecycle service not available')
                return False
            self.get_logger().info(f'Waiting for {name} lifecycle service...')

        while rclpy.ok():
            req = GetState.Request()
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self, future)

            if future.result().current_state.label == 'active':
                return True

            if (self.get_clock().now() - start_time).nanoseconds * 1e-9 > timeout:
                self.get_logger().error(f'{name} did not reach ACTIVE state')
                return False

            self.get_logger().info(f'{name} not active yet...')
            rclpy.sleep(1.0)

    # ============================================================
    # ROUTE COMPUTATION
    # ============================================================

    def getRoute(
        self,
        start: Union[int, PoseStamped],
        goal: Union[int, PoseStamped],
    ) -> Optional[List[Union[Path, Route]]]:
        """
        Compute a route without executing it.
        """

        self._waitForServer(self.compute_route_client)

        goal_msg = ComputeRoute.Goal()

        if isinstance(start, int):
            goal_msg.start_id = start
            goal_msg.goal_id = goal
            goal_msg.use_poses = False
            self.get_logger().info(f'Computing route from node {start} → {goal}')
        else:
            goal_msg.start = start
            goal_msg.goal = goal
            goal_msg.use_poses = True
            self.get_logger().info('Computing route from poses')

        future = self.compute_route_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)

        handle = future.result()
        if not handle.accepted:
            self.get_logger().error('ComputeRoute goal rejected')
            return None

        result_future = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result()
        if result.status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error('ComputeRoute failed')
            return None

        self.get_logger().info('Route successfully computed')
        return [result.result.path, result.result.route]

    # ============================================================
    # ROUTE EXECUTION
    # ============================================================

    def computeAndTrackRoute(
        self,
        start: Union[int, PoseStamped],
        goal: Union[int, PoseStamped],
    ) -> Optional[RunningTask]:
        """
        Compute and execute a route via route_server.
        """

        self._waitForServer(self.compute_and_track_route_client)

        goal_msg = ComputeAndTrackRoute.Goal()

        if isinstance(start, int):
            goal_msg.start_id = start
            goal_msg.goal_id = goal
            goal_msg.use_poses = False
            self.get_logger().info(f'Executing route {start} → {goal}')
        else:
            goal_msg.start = start
            goal_msg.goal = goal
            goal_msg.use_poses = True
            self.get_logger().info('Executing pose-based route')

        future = self.compute_and_track_route_client.send_goal_async(
            goal_msg,
            feedback_callback=self._routeFeedbackCallback
        )
        rclpy.spin_until_future_complete(self, future)

        self._route_goal_handle = future.result()
        if not self._route_goal_handle.accepted:
            self.get_logger().error('ComputeAndTrackRoute rejected')
            return None

        self._route_result_future = self._route_goal_handle.get_result_async()
        return RunningTask.COMPUTE_AND_TRACK_ROUTE

    def followPath(self, path: Path) -> Optional[RunningTask]:
        """
        Directly send a Path to controller_server.
        """

        self._waitForServer(self.follow_path_client)

        self.get_logger().info('Sending path to controller_server')

        goal_msg = FollowPath.Goal()
        goal_msg.path = path

        future = self.follow_path_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)

        self._follow_goal_handle = future.result()
        if not self._follow_goal_handle.accepted:
            self.get_logger().error('FollowPath rejected')
            return None

        self._follow_result_future = self._follow_goal_handle.get_result_async()
        return RunningTask.FOLLOW_PATH

    # ============================================================
    # TASK MONITORING
    # ============================================================

    def isTaskComplete(self, task: RunningTask) -> bool:
        future = None

        if task == RunningTask.COMPUTE_AND_TRACK_ROUTE:
            future = self._route_result_future
        elif task == RunningTask.FOLLOW_PATH:
            future = self._follow_result_future

        if future is None:
            return True

        rclpy.spin_until_future_complete(self, future, timeout_sec=0.1)
        if future.done():
            self._status = future.result().status
            return True

        return False

    def getFeedback(self):
        if self._route_feedback_queue:
            return self._route_feedback_queue.pop(0)
        return None

    def getResult(self) -> TaskResult:
        if self._status == GoalStatus.STATUS_SUCCEEDED:
            return TaskResult.SUCCEEDED
        if self._status == GoalStatus.STATUS_CANCELED:
            return TaskResult.CANCELED
        if self._status == GoalStatus.STATUS_ABORTED:
            return TaskResult.FAILED
        return TaskResult.UNKNOWN

    def cancel(self):
        self.get_logger().warn('Canceling current task')
        if self._route_goal_handle:
            self._route_goal_handle.cancel_goal_async()
        if self._follow_goal_handle:
            self._follow_goal_handle.cancel_goal_async()

    # ============================================================
    # INTERNALS
    # ============================================================

    def _routeFeedbackCallback(self, msg):
        self._route_feedback_queue.append(msg.feedback)

    def _waitForServer(self, client: ActionClient):
        while not client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info(f'Waiting for action server: {client.action_name}')
