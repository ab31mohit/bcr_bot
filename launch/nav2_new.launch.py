import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml

def generate_launch_description():
    pkg_nav2_dir = get_package_share_directory('nav2_bringup')
    pkg_bcr = get_package_share_directory('bcr_bot')

    use_sim_time = LaunchConfiguration('use_sim_time', default='True')
    autostart = LaunchConfiguration('autostart', default='True')

    route_params_file = LaunchConfiguration('route_params_file')
    route_graph_file = LaunchConfiguration('route_graph_file')     # Absolute path to the .geojson graph file

    declare_route_params_cmd = DeclareLaunchArgument(
        'route_params_file',
        default_value=os.path.join(pkg_bcr, 'config', 'nav2_route.yaml'),
        description='Nav2 parameters file for route server'
    )

    declare_route_graph_cmd = DeclareLaunchArgument(
        'route_graph_file',
        default_value=os.path.join(pkg_bcr, 'graphs', 'route_graph.geojson'),
        description='Route graph GeoJSON file for route server'
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
    )

    # Rewrite YAML to inject runtime values (graph_filepath, use_sim_time)
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=route_params_file,
            root_key='',
            param_rewrites={
                'use_sim_time': use_sim_time,
                'graph_filepath': route_graph_file
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
            'params_file': os.path.join(pkg_bcr, 'config', 'nav2_params.yaml'),
            'package_path': pkg_bcr, 
        }.items()
    )

    rviz_launch_cmd = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=[
            '-d' + os.path.join(
                # get_package_share_directory('nav2_bringup'),
                get_package_share_directory('bcr_bot'),
                'rviz',
                'nav2_new.rviz'
            )
        ]
    )
    
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[os.path.join(pkg_bcr, 'config', 'amcl_params.yaml')],
    )

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': os.path.join(pkg_bcr, 'config', 'bcr_map.yaml')}],
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
        executable='remapper.py',
        name='remapper',
        output='screen',
    )

    route_server_node = Node(
        package='nav2_route',
        executable='route_server',
        name='route_server',
        output='screen',
        parameters=[configured_params]   # passing the rewritten params to resolve geojson file path
    )

    route_lifecycle_mgr_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='route_lifecycle_manager',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': ['route_server']
            }
        ]
    )

    ld = LaunchDescription()

    ld.add_action(nav2_launch_cmd)
    ld.add_action(rviz_launch_cmd)
    ld.add_action(amcl_node)
    ld.add_action(map_server_node)
    ld.add_action(static_transform_publisher_node)
    ld.add_action(remapper_node)
    ld.add_action(declare_route_params_cmd)
    ld.add_action(declare_route_graph_cmd)
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(route_server_node)
    ld.add_action(route_lifecycle_mgr_node)

    return ld

