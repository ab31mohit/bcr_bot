import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml

def generate_launch_description():
    pkg_nav2_dir = get_package_share_directory('nav2_bringup')
    pkg_bcr = get_package_share_directory('bcr_bot')

    use_sim_time = LaunchConfiguration('use_sim_time', default='True')
    autostart = LaunchConfiguration('autostart', default='True')
    graph_file = LaunchConfiguration('graph_file')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
    )

    declare_graph_file_cmd = DeclareLaunchArgument(
        'graph_file',
        default_value='demo_inspection.geojson',
        description='Route graph GeoJSON file'
    )

    graph_filepath = PathJoinSubstitution([
        pkg_bcr,
        'graphs',
        graph_file
    ])

    # Rewrite YAML to inject runtime values (graph_filepath, use_sim_time)
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=os.path.join(pkg_bcr, 'config', 'nav2_route.yaml'),
            root_key='',
            param_rewrites={
                'use_sim_time': use_sim_time,
                'graph_filepath': graph_filepath
            },
            convert_types=True
        ),
        allow_substs=True
    )


    nav2_launch_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav2_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'map': os.path.join(pkg_bcr, 'config', 'bcr_map.yaml'),
            'params_file': os.path.join(pkg_bcr, 'config', 'nav2_route.yaml'),
            'package_path': pkg_bcr, 
        }.items()
    )

    rviz_launch_cmd = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=[
            '-d' + os.path.join(
                get_package_share_directory('bcr_bot'),
                'rviz',
                'route_navigation.rviz'
            )
        ]
    )

    static_transform_publisher_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
    )

    remapper_node = Node(
        package='bcr_bot',
        executable='cmd_vel_remapper.py',
        name='cmd_vel_remapper',
        output='screen',
        parameters=[ {
                    'input_cmd_vel_topic': 'cmd_vel_collision',
                    'output_cmd_vel_topic': '/bcr_bot/cmd_vel'
        }]
    )

    route_server_node = Node(
        package='nav2_route',
        executable='route_server',
        name='route_server',
        output='screen',
        parameters=[configured_params]   # passing the rewritten params to resolve geojson file path
    )

    collision_monitor_node = Node(
        package='nav2_collision_monitor',
        executable='collision_monitor',
        name='collision_monitor',
        output='screen',
            parameters=[
                os.path.join(pkg_bcr, 'config', 'nav2_route.yaml'),
                {'use_sim_time': use_sim_time}
            ],
    )

    route_lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='route_lifecycle_manager',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': ['route_server', 'collision_monitor']
            }
        ]
    )

    ld = LaunchDescription()

    ld.add_action(nav2_launch_cmd)
    ld.add_action(rviz_launch_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_graph_file_cmd)
    ld.add_action(static_transform_publisher_node)
    ld.add_action(remapper_node)
    ld.add_action(route_server_node)
    ld.add_action(collision_monitor_node)
    ld.add_action(route_lifecycle_manager_node)

    return ld

