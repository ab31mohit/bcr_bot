from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    graph_file_arg = DeclareLaunchArgument(
        'graph_file',
        default_value='route_graph.geojson'
    )

    direction_arg = DeclareLaunchArgument(
        'direction',
        default_value='unidirectional',
        description='unidirectional or bidirectional'
    )>

    return LaunchDescription([
        graph_file_arg,
        direction_arg,

        Node(
            package='bcr_bot',
            executable='route_graph.py',
            output='screen',
            parameters=[{
                'graph_file': LaunchConfiguration('graph_file'),
                'direction': LaunchConfiguration('direction')
            }]
        )
    ])
