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

        # ---------------- Parameters ----------------
        self.declare_parameter('graph_file', 'route_graph.geojson')
        self.declare_parameter('direction', 'unidirectional')  # unidirectional | bidirectional

        self.graph_file = self.get_parameter('graph_file').value
        self.direction = self.get_parameter('direction').value.lower()

        if self.direction not in ['unidirectional', 'bidirectional']:
            self.get_logger().fatal("direction must be 'unidirectional' or 'bidirectional'")
            raise RuntimeError("Invalid direction parameter")

        # Namespace
        self.robot_ns = self.get_namespace().strip('/')

        # Output path (unchanged)
        self.output_dir = os.path.expanduser(
            "~/ros2_ws/src/bcr_bot/graphs"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, self.graph_file)

        # Internal state
        self.nodes = []
        self.edges = []
        self.path_poses = []

        self.node_id = 0
        self.edge_id = 100
        self.saved = False

        # Subscriptions
        self.create_subscription(
            PointStamped,
            "/clicked_point",
            self.clicked_point_cb,
            10
        )

        # Publishers
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

        self.get_logger().info("Route Graph Builder started")
        self.get_logger().info(f"Graph file: {self.output_file}")
        self.get_logger().info(f"Direction mode: {self.direction}")

    # --------------------------------------------------

    def clicked_point_cb(self, msg: PointStamped):
        x = round(msg.point.x, 3)
        y = round(msg.point.y, 3)

        nid = self.node_id
        self.node_id += 1

        # ---- Node ----
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

        # ---- Edge(s) ----
        if nid > 0:
            prev = self.nodes[nid - 1]["geometry"]["coordinates"]
            curr = [x, y]

            # Forward edge
            self.add_edge(nid - 1, nid, prev, curr)

            # Reverse edge (if bidirectional)
            if self.direction == "bidirectional":
                self.add_edge(nid, nid - 1, curr, prev)

        # ---- Path ----
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = 1.0
        self.path_poses.append(pose)

        self.publish_markers()
        self.publish_path()

        self.get_logger().info(f"Added node {nid} at ({x}, {y})")

    # --------------------------------------------------

    def add_edge(self, startid, endid, start_xy, end_xy):
        self.edges.append({
            "type": "Feature",
            "geometry": {
                "type": "MultiLineString",
                "coordinates": [[start_xy, end_xy]]
            },
            "properties": {
                "id": self.edge_id,
                "startid": startid,
                "endid": endid,
                "cost": 0.0,
                "overridable": True
            }
        })
        self.edge_id += 1

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
            m.scale.x = m.scale.y = m.scale.z = 0.25
            m.color.r = 1.0
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
            self.get_logger().warn("No nodes created. Nothing to save.")
            return

        geojson = {
            "type": "FeatureCollection",
            "name": "graph",
            "features": self.nodes + self.edges
        }

        with open(self.output_file, "w") as f:
            json.dump(geojson, f, indent=2)

        self.saved = True

        print("========== Route Graph Saved ==========")
        print(f"File      : {self.output_file}")
        print(f"Nodes     : {len(self.nodes)}")
        print(f"Edges     : {len(self.edges)}")
        print(f"Direction : {self.direction}")
        print("======================================")

def main():
    rclpy.init()
    node = RouteGraphBuilder()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down cleanly...")

    finally:
        node.save_geojson()
        # commented as they were giving warnings on (ctrl + c) shutdown.
        # node.destroy_node()
        # rclpy.shutdown()


if __name__ == "__main__":
    main()
