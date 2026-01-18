import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile

from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg_bcr = get_package_share_directory('bcr_bot')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    params_file = LaunchConfiguration('params_file')
    map_yaml_file = LaunchConfiguration('map_file')
    rviz_file = LaunchConfiguration('rviz_file')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically start lifecycle nodes'
    )

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_bcr, 'config', 'route_localization.yaml'),
        description='AMCL + Map Server parameter file'
    )

    declare_map_yaml_cmd = DeclareLaunchArgument(
        'map_file',
        default_value=os.path.join(pkg_bcr, 'config', 'bcr_map.yaml'),
        description='Map yaml file'
    )

    declare_rviz_file_cmd = DeclareLaunchArgument(
        'rviz_file',
        default_value='route_navigation.rviz',
        description='Rviz2 (.rviz) file'
    )

    # Parameters
    param_substitutions = {
        'use_sim_time': use_sim_time,
        'yaml_filename': map_yaml_file
    }

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key='',
            param_rewrites=param_substitutions,
            convert_types=True
        ),
        allow_substs=True
    )

    remappings = [
        ('/tf', 'tf'),
        ('/tf_static', 'tf_static')
    ]

    # Nodes
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[configured_params],
        remappings=remappings
    )

    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[configured_params],
        remappings=remappings
    )

    static_transform_publisher_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_odom',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=[
            '-d',
            PathJoinSubstitution([
                get_package_share_directory('bcr_bot'),
                'rviz',
                rviz_file
            ])
        ]
    )


    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'node_names': ['map_server', 'amcl']
        }]
    )

    # Launch description
    ld = LaunchDescription()

    ld.add_action(SetEnvironmentVariable(
        'RCUTILS_LOGGING_BUFFERED_STREAM', '1'
    ))

    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_map_yaml_cmd)
    ld.add_action(declare_rviz_file_cmd)

    ld.add_action(map_server_node)
    ld.add_action(amcl_node)
    ld.add_action(static_transform_publisher_node)
    ld.add_action(rviz_node)
    ld.add_action(lifecycle_manager_node)

    return ld
