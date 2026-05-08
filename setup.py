from glob import glob

from setuptools import find_packages, setup


package_name = "jarvis"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ssu",
    maintainer_email="ssu@todo.todo",
    description="Jarvis dispenser press task package for Doosan ROS2.",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "dispenser_press_node = jarvis.dispenser_press_node:main",
        ],
    },
)
