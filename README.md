# BCR Bot

https://github.com/blackcoffeerobotics/bcr_bot/assets/13151010/0fc570a3-c70c-415b-8222-b9573d5911c8

## About

This repository contains a Gazebo and Isaac Sim simulation for a differential drive robot, equipped with an IMU, a depth camera, stereo camera and a 2D LiDAR. The primary contriution of this project is to support multiple ROS and Gazebo distros. Currently, the project supports the following versions - 

1. [ROS Noetic + Gazebo Classic 11 (branch ros1)](#noetic--classic-ubuntu-2004)
2. [ROS2 Humble + Gazebo Classic 11 (branch ros2)](#humble--classic-ubuntu-2204)
3. [ROS2 Humble + Gazebo Fortress (branch ros2)](#humble--fortress-ubuntu-2204)
4. [ROS2 Humble + Gazebo Harmonic (branch ros2)](#humble--harmonic-ubuntu-2204)
5. [ROS2 Humble + Isaac Sim (branch ros2)](#humble--isaac-sim-ubuntu-2204)

The complete information on how to use this project is decribed in [OLDREADME.md](OLDREADME.md).    

This [README.md](README.md) describes how to use this project in ROS2 Humle with GZ Harmonic on Ubuntu 22.04.  

## Humble + Harmonic (Ubuntu 22.04)

### Dependencies

In addition to ROS2 Humble and [Gazebo Harmonic installations](https://gazebosim.org/docs/harmonic/install_ubuntu), we need to manually install interfaces between ROS2 and Gazebo sim as follows,

```bash
sudo apt-get install ros-humble-ros-gzharmonic
```
Remainder of the dependencies can be installed with [rosdep](http://wiki.ros.org/rosdep)

```bash
# From the root directory of the workspace. This will install everything mentioned in package.xml
rosdep install --from-paths src --ignore-src -r -y
```

### Build

```bash
colcon build --packages-select bcr_bot
```

## Bringup & Navigation

### 1. Start robot simulation

- The launch file accepts multiple launch arguments

    ```bash
    ros2 launch bcr_bot gz.launch.py \
        camera_enabled:=True \
        stereo_camera_enabled:=False \
        two_d_lidar_enabled:=True \
        position_x:=0.0 \
        position_y:=0.0  \
        orientation_yaw:=0.0 \
        odometry_source:=world \
        world_file:=small_warehouse.sdf
    ```

    ![small_warehouse World](res/gz.jpg)

### 2. Localization & navigation

Nav2 is an open-source navigation package that enables a robot to navigate through an environment easily. It takes laser scan and odometry data, along with the map of the environment, as inputs.

1. For running free space (spatial) navigation :   

    ```bash
    ros2 launch bcr_bot nav2.launch.py
    ```   

    This will start localization, planners & navigation.   
    We can pass 2D Nav goal from rviz and then robot will plan & navigate on itsef.   

- For running route graph based navigation :  

    ```bash
    ros2 launch bcr_bot nav2_route.launch.py graph_file:=bcr1.geojson
    ```   

    This launch file contains the same structure of the original [nav2.launch.py](launch/nav2.launch.py) with addition to route_server & collision_monitor.   

- For building a custom route graph run :  

    ```bash
    ros2 launch bcr_bot route_localization.launch.py rviz_file:=route_graph.rviz
    ```   

    This will launch the localization file and publish map (considdering bringup is already running).   
    Then we can run the route graph launch file for building the graph :  

    ```bash
    ros2 launch bcr_bot route_graph.launch.py graph_file:=my_graph.geojson direction:=unidirectional
    ```    
    then use the **publish point** button rviz2 screen to create nodes on the graph and then when you're done, press `ctrl +  c` to exit the node.   

- For using only the minimal code for localization & route navigation run :  

    ```bash
    ros2 launch bcr_bot route_localization.launch.py
    ```   
    This will start the localization on a predefined map file in rviz.    

    Now run the route navigation :    

    ```bash
    ros2 launch bcr_bot route_navigation.launch.py graph_file:=demo_inspection.geojson
    ```   

    This will launch the route navigation nodes with custom route graph.    

- For route navigation there are 2 options :  

    1. Goal id based single route navigation mission   

        ```bash
        ros2 launch bcr_bot follow_route_node.launch.py start_node:=0 goal_node:=6
        ```    
        This will take only one pair of (start,goal) node ids of the route graph and then reach the goal node along the calculated path on the graph with collision monitor (stop when obstacle come in front of it).   

    2. Looping of route graph navigation :  

        ```bash
        ros2 run bcr_bot demo_inspection.py
        ```    
        this uses a node_array type node id based array for specifying which nodes to follow one after the other.  
          
    ---
    **NOTE:**   
    The current issue in [follow_route_node.py](scripts/follow_route_node.py) & [demo_inspection.py](scripts/demo_inspection.py) files is that when an obstacle come in front of the robot, the route navigation collapses and only the current goal is reached. 



