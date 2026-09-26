from setuptools import find_packages, setup


package_name = 'eyecar_led'


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
    description='ROS 2 driver for the EyeCar WS281x status strip.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'led_strip = eyecar_led.led_strip:main',
        ],
    },
)
