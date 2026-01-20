import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration, EnvironmentVariable, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():

    pkg_bcr = get_package_share_directory('bcr_bot')

    # Configuring launch arguments
    params_file = LaunchConfiguration('params_file')
    graph_file = LaunchConfiguration('graph_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Declaring launch argument values
    declare_params_file = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_bcr, 'config', 'route_navigation.yaml'),
        description='Nav2 parameters file'
    )

    declare_graph_file = DeclareLaunchArgument(
        'graph_file',
        default_value='demo_inspection.geojson',
        description='Route graph GeoJSON file'
    )

    graph_filepath = PathJoinSubstitution([
        pkg_bcr,
        'graphs',
        graph_file
    ])

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='True'
    )

    # Launch multiple nodes in a group
    nav2_nodes = GroupAction([

        Node(
            package='nav2_controller',
            executable='controller_server',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time}
            ],
            remappings=[
                ('cmd_vel', 'cmd_vel_nav')       # this velocity topic will be input for the velocity_smoother
            ]
        ),

        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            name='velocity_smoother',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time}
            ],
            remappings=[
                ('cmd_vel', 'cmd_vel_nav')       # input velocity topic to filter (output is cmd_vel_smoothed)
            ]
        ),

        Node(
            package='nav2_route',
            executable='route_server',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time,
                'graph_filepath': graph_filepath
                }
            ],
        ),

        Node(
            package='nav2_collision_monitor',
            executable='collision_monitor',
            name='collision_monitor',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time}
            ],
        ),

        Node(
            package='nav2_planner',
            executable='planner_server',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time}
            ],
        ),

        Node(
            package='nav2_smoother',
            executable='smoother_server',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time}
            ],
        ),

        Node(
            package='bcr_bot',
            executable='cmd_vel_remapper.py',
            name='cmd_vel_remapper',
            output='screen',
            parameters=[ {
                    'cmd_vel_topic_in': 'cmd_vel',
                    'cmd_vel_topic_out': '/bcr_bot/cmd_vel'
            }]
        ),

        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': [
                    'controller_server',
                    'velocity_smoother',
                    'route_server',
                    'collision_monitor',
                    'planner_server',
                    'smoother_server',
                ]
            }]
        ),
    ])

    return LaunchDescription([
        declare_params_file,
        declare_graph_file,
        declare_use_sim_time,
        nav2_nodes
    ])