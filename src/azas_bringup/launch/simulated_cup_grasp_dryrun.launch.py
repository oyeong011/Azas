from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    cup_detection_topic = LaunchConfiguration("cup_detection_topic")
    tumbler_pose_topic = LaunchConfiguration("tumbler_pose_topic")

    floor_place_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("jarvis"), "launch", "tumbler_floor_place.launch.py"])
        ),
        launch_arguments={
            "selected_dispenser_id": LaunchConfiguration("selected_dispenser_id"),
            "use_tumbler_pose_topic": "true",
            "tumbler_pose_topic": tumbler_pose_topic,
            "allow_demo_tumbler_position_fallback": "false",
            "tumbler_pose_wait_timeout": LaunchConfiguration("tumbler_pose_wait_timeout"),
            "enable_hardware": "false",
            "hardware_confirm": "",
            "allow_service_control_without_moveit": "false",
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("selected_dispenser_id", default_value="2"),
        DeclareLaunchArgument("cup_detection_topic", default_value="/azas/sim/cup_detection"),
        DeclareLaunchArgument("tumbler_pose_topic", default_value="/azas/sim/tumbler_pose"),
        DeclareLaunchArgument("tumbler_pose_wait_timeout", default_value="8.0"),
        DeclareLaunchArgument("frame_id", default_value="base_link"),
        DeclareLaunchArgument("confidence", default_value="0.95"),
        DeclareLaunchArgument("bridge_min_confidence", default_value="0.35"),
        DeclareLaunchArgument("planning_group", default_value=""),
        DeclareLaunchArgument("ee_link", default_value=""),
        DeclareLaunchArgument("publish_once", default_value="true"),
        DeclareLaunchArgument("grasp_x", default_value="0.32"),
        DeclareLaunchArgument("grasp_y", default_value="-0.22"),
        DeclareLaunchArgument("grasp_z", default_value="0.05"),
        DeclareLaunchArgument("mouth_x", default_value="0.32"),
        DeclareLaunchArgument("mouth_y", default_value="-0.22"),
        DeclareLaunchArgument("mouth_z", default_value="0.22"),
        Node(
            package="azas_perception",
            executable="simulated_cup_detection_node",
            name="simulated_cup_detection_node",
            output="screen",
            parameters=[{
                "output_topic": cup_detection_topic,
                "frame_id": LaunchConfiguration("frame_id"),
                "confidence": ParameterValue(LaunchConfiguration("confidence"), value_type=float),
                "publish_once": ParameterValue(LaunchConfiguration("publish_once"), value_type=bool),
                "grasp_x": ParameterValue(LaunchConfiguration("grasp_x"), value_type=float),
                "grasp_y": ParameterValue(LaunchConfiguration("grasp_y"), value_type=float),
                "grasp_z": ParameterValue(LaunchConfiguration("grasp_z"), value_type=float),
                "mouth_x": ParameterValue(LaunchConfiguration("mouth_x"), value_type=float),
                "mouth_y": ParameterValue(LaunchConfiguration("mouth_y"), value_type=float),
                "mouth_z": ParameterValue(LaunchConfiguration("mouth_z"), value_type=float),
            }],
        ),
        Node(
            package="azas_perception",
            executable="cup_detection_pose_bridge_node",
            name="simulated_cup_pose_bridge_node",
            output="screen",
            parameters=[{
                "input_topic": cup_detection_topic,
                "output_topic": tumbler_pose_topic,
                "min_confidence": ParameterValue(LaunchConfiguration("bridge_min_confidence"), value_type=float),
                "target_frame": LaunchConfiguration("frame_id"),
                "require_tf": False,
            }],
        ),
        Node(
            package="azas_motion",
            executable="alignment_executor_node",
            name="side_grasp_planning_only_checker",
            output="screen",
            parameters=[{
                "enable_planning_only": True,
                "allow_execute": False,
                "planning_group": LaunchConfiguration("planning_group"),
                "ee_link": LaunchConfiguration("ee_link"),
                "base_frame": LaunchConfiguration("frame_id"),
            }],
        ),
        floor_place_launch,
    ])
