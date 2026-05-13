from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    run_grounded_sam2_adapter = LaunchConfiguration("run_grounded_sam2_adapter")

    grounded_sam2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("azas_bringup"), "launch", "grounded_sam2_perception.launch.py"])
        ),
        launch_arguments={
            "mask_topic": LaunchConfiguration("mask_topic"),
            "depth_topic": LaunchConfiguration("depth_topic"),
            "camera_info_topic": LaunchConfiguration("camera_info_topic"),
            "depth_scale": LaunchConfiguration("depth_scale"),
            "mask_threshold": LaunchConfiguration("mask_threshold"),
            "min_mask_pixels": LaunchConfiguration("min_mask_pixels"),
            "cup_height_m": LaunchConfiguration("cup_height_m"),
            "default_confidence": LaunchConfiguration("default_confidence"),
            "target_prompt": LaunchConfiguration("target_prompt"),
        }.items(),
        condition=IfCondition(run_grounded_sam2_adapter),
    )

    floor_place_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("jarvis"), "launch", "tumbler_floor_place.launch.py"])
        ),
        launch_arguments={
            "selected_dispenser_id": LaunchConfiguration("selected_dispenser_id"),
            "use_tumbler_pose_topic": "true",
            "tumbler_pose_topic": "/jarvis/tumbler_dispenser/tumbler_pose",
            "allow_demo_tumbler_position_fallback": "false",
            "tumbler_pose_wait_timeout": LaunchConfiguration("tumbler_pose_wait_timeout"),
            "enable_hardware": LaunchConfiguration("enable_hardware"),
            "hardware_confirm": LaunchConfiguration("hardware_confirm"),
            "allow_service_control_without_moveit": LaunchConfiguration("allow_service_control_without_moveit"),
            "gripper_open_service": "/jarvis/rg2/open",
            "gripper_close_service": "/jarvis/rg2/close",
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("selected_dispenser_id", default_value="1"),
        DeclareLaunchArgument("mask_topic", default_value="/grounded_sam2/tumbler_mask"),
        DeclareLaunchArgument("depth_topic", default_value="/camera/aligned_depth_to_color/image_raw"),
        DeclareLaunchArgument("camera_info_topic", default_value="/camera/color/camera_info"),
        DeclareLaunchArgument("depth_scale", default_value="0.001"),
        DeclareLaunchArgument("mask_threshold", default_value="1"),
        DeclareLaunchArgument("min_mask_pixels", default_value="80"),
        DeclareLaunchArgument("cup_height_m", default_value="0.17"),
        DeclareLaunchArgument("default_confidence", default_value="0.75"),
        DeclareLaunchArgument("target_prompt", default_value="tumbler cup"),
        DeclareLaunchArgument("run_grounded_sam2_adapter", default_value="true"),
        DeclareLaunchArgument("enable_hardware", default_value="false"),
        DeclareLaunchArgument("hardware_confirm", default_value=""),
        DeclareLaunchArgument("allow_service_control_without_moveit", default_value="false"),
        DeclareLaunchArgument("tumbler_pose_wait_timeout", default_value="30.0"),
        grounded_sam2_launch,
        Node(
            package="azas_perception",
            executable="cup_detection_pose_bridge_node",
            name="cup_detection_pose_bridge_node",
            output="screen",
            parameters=[{
                "min_confidence": ParameterValue(LaunchConfiguration("default_confidence"), value_type=float),
            }],
        ),
        floor_place_launch,
    ])
