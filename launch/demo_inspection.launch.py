from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():

    return LaunchDescription([

        DeclareLaunchArgument(
            'start_node',
            default_value='0'
        ),

        DeclareLaunchArgument(
            'loop_nodes',
            default_value='[2, 6]'
        ),

        DeclareLaunchArgument(
            'loop_count',
            default_value='2'
        ),

        DeclareLaunchArgument(
            'return_node',
            default_value='0'
        ),

        Node(
            package='bcr_bot',
            executable='demo_inspection.py',
            name='demo_inspection_node',
            output='screen',
            parameters=[{
                'start_node': LaunchConfiguration('start_node'),
                'loop_nodes': LaunchConfiguration('loop_nodes'),
                'loop_count': LaunchConfiguration('loop_count'),
                'return_node': LaunchConfiguration('return_node'),
            }]
        )
    ])
