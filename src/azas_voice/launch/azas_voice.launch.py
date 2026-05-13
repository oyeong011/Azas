from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_live_stt = LaunchConfiguration("use_live_stt")
    stt_topic = LaunchConfiguration("stt_topic")

    return LaunchDescription(
        [
            DeclareLaunchArgument("use_live_stt", default_value="false"),
            DeclareLaunchArgument("stt_topic", default_value="/stt_result"),
            Node(
                package="azas_voice",
                executable="recipe_mapper_node",
                name="recipe_mapper_node",
                output="screen",
                parameters=[{"stt_topic": stt_topic}],
            ),
            Node(
                package="azas_voice",
                executable="stt_node",
                name="stt_node",
                output="screen",
                parameters=[{"stt_topic": stt_topic}],
                condition=IfCondition(use_live_stt),
            ),
        ]
    )
