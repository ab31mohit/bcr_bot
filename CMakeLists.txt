cmake_minimum_required(VERSION 3.5)
project(bcr_bot)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch meshes models urdf worlds rviz
    DESTINATION share/${PROJECT_NAME}/
)

install( DIRECTORY config/
         DESTINATION share/${PROJECT_NAME}/config)

install( DIRECTORY graphs/
         DESTINATION share/${PROJECT_NAME}/graphs)
         
         
install(PROGRAMS 
    scripts/remapper.py
    scripts/teleop_keyboard.py
    scripts/route_graph.py
    scripts/route_navigator.py
    scripts/follow_route.py
    DESTINATION lib/${PROJECT_NAME})

ament_package()
