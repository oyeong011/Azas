from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("mask_topic", default_value="/grounded_sam2/tumbler_mask"),
        DeclareLaunchArgument("depth_topic", default_value="/camera/aligned_depth_to_color/image_raw"),
        DeclareLaunchArgument("camera_info_topic", default_value="/camera/color/camera_info"),
        DeclareLaunchArgument("depth_scale", default_value="0.001"),
        DeclareLaunchArgument("mask_threshold", default_value="1"),
        DeclareLaunchArgument("min_mask_pixels", default_value="80"),
        DeclareLaunchArgument("cup_height_m", default_value="0.17"),
        DeclareLaunchArgument("default_confidence", default_value="0.75"),
        DeclareLaunchArgument("target_prompt", default_value="tumbler cup"),
        Node(
            package="azas_perception",
            executable="grounded_sam2_mask_detector_node",
            name="grounded_sam2_mask_detector_node",
            output="screen",
            parameters=[{
                "mask_topic": LaunchConfiguration("mask_topic"),
                "depth_topic": LaunchConfiguration("depth_topic"),
                "camera_info_topic": LaunchConfiguration("camera_info_topic"),
                "depth_scale": ParameterValue(LaunchConfiguration("depth_scale"), value_type=float),
                "mask_threshold": ParameterValue(LaunchConfiguration("mask_threshold"), value_type=int),
                "min_mask_pixels": ParameterValue(LaunchConfiguration("min_mask_pixels"), value_type=int),
                "cup_height_m": ParameterValue(LaunchConfiguration("cup_height_m"), value_type=float),
                "default_confidence": ParameterValue(LaunchConfiguration("default_confidence"), value_type=float),
                "target_prompt": LaunchConfiguration("target_prompt"),
            }],
        ),
    ])
