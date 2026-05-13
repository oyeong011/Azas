from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    run_mask_runner = LaunchConfiguration("run_mask_runner")

    floor_place_pipeline = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("azas_bringup"), "launch", "grounded_sam2_to_floor_place.launch.py"])
        ),
        launch_arguments={
            "selected_dispenser_id": LaunchConfiguration("selected_dispenser_id"),
            "mask_topic": LaunchConfiguration("mask_topic"),
            "depth_topic": LaunchConfiguration("depth_topic"),
            "camera_info_topic": LaunchConfiguration("camera_info_topic"),
            "depth_scale": LaunchConfiguration("depth_scale"),
            "mask_threshold": LaunchConfiguration("mask_threshold"),
            "min_mask_pixels": LaunchConfiguration("min_mask_pixels"),
            "cup_height_m": LaunchConfiguration("cup_height_m"),
            "default_confidence": LaunchConfiguration("default_confidence"),
            "target_prompt": LaunchConfiguration("prompt"),
            "enable_hardware": LaunchConfiguration("enable_hardware"),
            "hardware_confirm": LaunchConfiguration("hardware_confirm"),
            "allow_service_control_without_moveit": LaunchConfiguration("allow_service_control_without_moveit"),
            "tumbler_pose_wait_timeout": LaunchConfiguration("tumbler_pose_wait_timeout"),
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("selected_dispenser_id", default_value="1"),
        DeclareLaunchArgument("color_topic", default_value="/camera/color/image_raw"),
        DeclareLaunchArgument("depth_topic", default_value="/camera/aligned_depth_to_color/image_raw"),
        DeclareLaunchArgument("camera_info_topic", default_value="/camera/color/camera_info"),
        DeclareLaunchArgument("mask_topic", default_value="/grounded_sam2/tumbler_mask"),
        DeclareLaunchArgument("prompt", default_value="tumbler cup"),
        DeclareLaunchArgument("min_score", default_value="0.25"),
        DeclareLaunchArgument("depth_scale", default_value="0.001"),
        DeclareLaunchArgument("mask_threshold", default_value="1"),
        DeclareLaunchArgument("min_mask_pixels", default_value="80"),
        DeclareLaunchArgument("cup_height_m", default_value="0.17"),
        DeclareLaunchArgument("default_confidence", default_value="0.75"),
        DeclareLaunchArgument("run_mask_runner", default_value="true"),
        DeclareLaunchArgument("enable_hardware", default_value="false"),
        DeclareLaunchArgument("hardware_confirm", default_value=""),
        DeclareLaunchArgument("allow_service_control_without_moveit", default_value="false"),
        DeclareLaunchArgument("tumbler_pose_wait_timeout", default_value="30.0"),
        Node(
            package="azas_perception",
            executable="grounded_sam2_tumbler_mask_node",
            name="grounded_sam2_tumbler_mask_node",
            output="screen",
            parameters=[{
                "color_topic": LaunchConfiguration("color_topic"),
                "mask_topic": LaunchConfiguration("mask_topic"),
                "prompt": LaunchConfiguration("prompt"),
                "min_score": ParameterValue(LaunchConfiguration("min_score"), value_type=float),
            }],
            condition=IfCondition(run_mask_runner),
        ),
        floor_place_pipeline,
    ])
