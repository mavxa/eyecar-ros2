from setuptools import find_packages, setup


package_name = 'eyecar_web'


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
    description='Minimal ROS 2 WebSocket bridge for the EyeCar panel.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'web_bridge = eyecar_web.web_bridge:main',
        ],
    },
)
