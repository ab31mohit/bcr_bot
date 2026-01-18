from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    start_node_arg = DeclareLaunchArgument(
        'start_node',
        default_value='0',
        description='Start node ID'
    )

    goal_node_arg = DeclareLaunchArgument(
        'goal_node',
        default_value='1',
        description='Goal node ID'
    )

    return LaunchDescription([
        start_node_arg,
        goal_node_arg,

        Node(
            package='bcr_bot',
            executable='follow_route_node.py',
            name='route_follower_node',
            output='screen',
            parameters=[{
                'start_node': LaunchConfiguration('start_node'),
                'goal_node': LaunchConfiguration('goal_node')
            }]
        )
    ])
