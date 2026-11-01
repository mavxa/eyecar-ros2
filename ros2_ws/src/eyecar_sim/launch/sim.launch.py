import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.webots_launcher import WebotsLauncher


def generate_launch_description():
    if os.environ.get('ROS_DOMAIN_ID', '0') == '0':
        raise RuntimeError('Use a separate simulation domain, for example ROS_DOMAIN_ID=42')
    package = Path(get_package_share_directory('eyecar_sim'))
    description = package / 'config/eyecar.urdf'
    webots = WebotsLauncher(world=str(package / 'worlds/practice.wbt'),
                           gui=LaunchConfiguration('gui'))
    driver = WebotsController(robot_name='eyecar',
                              parameters=[{'robot_description': str(description)}])
    model = Node(package='robot_state_publisher', executable='robot_state_publisher',
                 parameters=[{'robot_description': description.read_text(), 'use_sim_time': True}])
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true'), webots, driver, model,
        RegisterEventHandler(OnProcessExit(target_action=webots,
                                           on_exit=[EmitEvent(event=Shutdown())])),
    ])
