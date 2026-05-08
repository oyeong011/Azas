from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    dispenser_press_params = {
        # If dsr_bringup2 is launched with name:=dsr01, set this to "dsr01".
        "service_prefix": "",
        # HOME 도착 후 현재 TCP 위치를 펌프 위 30 mm approach pose로 사용합니다.
        "use_home_as_reference": True,
        # base_link 기준 디스펜서 펌프 상단 중앙 위치입니다.
        # use_home_as_reference=False일 때만 사용됩니다.
        "dispenser_x": 0.50,
        "dispenser_y": 0.00,
        "dispenser_top_z": 0.37,
        "approach_height": 0.03,
        "press_depth": 0.015,
        "hold_seconds": 0.5,
        "move_home_first": True,
        "return_home": True,
        # Doosan posx orientation is rx, ry, rz in degrees.
        "rx": 180.0,
        "ry": 0.0,
        "rz": 180.0,
        "home_joints_deg": [0.0, 0.0, 90.0, 0.0, 90.0, 0.0],
        "joint_velocity": 20.0,
        "joint_acceleration": 20.0,
        "line_velocity": 30.0,
        "line_acceleration": 50.0,
    }

    return LaunchDescription(
        [
            Node(
                package="jarvis",
                executable="dispenser_press_node",
                output="screen",
                parameters=[
                    dispenser_press_params,
                ],
            )
        ]
    )
