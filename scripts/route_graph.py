#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PointStamped, PoseStamped
from visualization_msgs.msg import Marker, MarkerArray
from nav_msgs.msg import Path

import json
import os


class RouteGraphBuilder(Node):

    def __init__(self):
        super().__init__('route_graph_builder_node')

        # Parameters
        self.declare_parameter('graph_file', 'route_graph.geojson')
        graph_file = self.get_parameter('graph_file').get_parameter_value().string_value

        # Namespace info
        self.robot_ns = ''

        # Output path
        self.output_dir = os.path.expanduser(
            "~/ros2_ws/src/bcr_bot/graphs"
        )
        os.makedirs(self.output_dir, exist_ok=True)

        self.output_file = os.path.join(self.output_dir, graph_file)

        # Internal state
        self.nodes = []
        self.edges = []
        self.path_poses = []

        self.node_id = 0
        self.edge_id = 100
        self.saved = False

        # Subscriptions (from rviz2 click event)
        self.create_subscription(
            PointStamped,
            "/clicked_point",
            self.clicked_point_cb,
            10
        )

        # Publishers (namespaced)
        self.marker_pub = self.create_publisher(
            MarkerArray,
            "route_graph/marker_array",
            10
        )

        self.path_pub = self.create_publisher(
            Path,
            "route_graph/path",
            10
        )

        # Logs
        self.get_logger().info("Route Graph Builder started")
        self.get_logger().info(f"Robot namespace: '{self.robot_ns or '/'}'")
        self.get_logger().info(f"Graph file: {self.output_file}")
        self.get_logger().info("Click points in RViz (Publish Point)")
        self.get_logger().info("Press Ctrl+C to save")

    # --------------------------------------------------

    def clicked_point_cb(self, msg: PointStamped):
        x = msg.point.x
        y = msg.point.y

        nid = self.node_id
        self.node_id += 1

        # GeoJSON node
        self.nodes.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [x, y]
            },
            "properties": {
                "id": nid,
                "frame": "map"
            }
        })

        # Sequential edge
        if nid > 0:
            self.edges.append({
                "type": "Feature",
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": []
                },
                "properties": {
                    "id": self.edge_id,
                    "startid": nid - 1,
                    "endid": nid,
                    "cost": 0.0,
                    "overridable": True
                }
            })
            self.edge_id += 1

        # Path pose
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = 1.0
        self.path_poses.append(pose)

        self.publish_markers()
        self.publish_path()

        self.get_logger().info(
            f"[{self.robot_ns or '/'}] Added waypoint {nid} at ({x:.2f}, {y:.2f})"
        )

    # --------------------------------------------------

    def publish_markers(self):
        ma = MarkerArray()

        for i, pose in enumerate(self.path_poses):
            m = Marker()
            m.header.frame_id = "map"
            m.ns = "waypoints"
            m.id = i
            m.type = Marker.SPHERE
            m.action = Marker.ADD
            m.pose = pose.pose
            m.scale.x = 0.25
            m.scale.y = 0.25
            m.scale.z = 0.25
            m.color.r = 1.0
            m.color.g = 0.0
            m.color.b = 0.0
            m.color.a = 1.0
            ma.markers.append(m)

        self.marker_pub.publish(ma)

    # --------------------------------------------------

    def publish_path(self):
        path = Path()
        path.header.frame_id = "map"
        path.poses = self.path_poses
        self.path_pub.publish(path)

    # --------------------------------------------------

    def save_geojson(self):
        if self.saved:
            return

        if not self.nodes:
            self.get_logger().warn("No waypoints collected. Nothing to save.")
            return

        geojson = {
            "type": "FeatureCollection",
            "name": "graph",
            "features": self.nodes + self.edges
        }

        with open(self.output_file, "w") as f:
            json.dump(geojson, f, indent=2)

        self.saved = True
        self.get_logger().info(f"Saved route graph to:\n{self.output_file}")


def main():
    rclpy.init()
    node = RouteGraphBuilder()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Ctrl+C pressed")
    finally:
        node.save_geojson()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()