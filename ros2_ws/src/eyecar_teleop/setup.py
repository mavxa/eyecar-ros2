from setuptools import find_packages, setup


package_name = 'eyecar_teleop'


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mavxa',
    maintainer_email='mavxa@users.noreply.github.com',
    description='Safe keyboard teleoperation for the EyeCar ROS 2 platform.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'keyboard_teleop = eyecar_teleop.keyboard_teleop:main',
            'cmd_vel_monitor = eyecar_teleop.cmd_vel_monitor:main',
        ],
    },
)
