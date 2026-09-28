from setuptools import find_packages, setup


setup(
    name='eyecar_camera',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/eyecar_camera']),
        ('share/eyecar_camera', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='mavxa',
    maintainer_email='mavxa@users.noreply.github.com',
    description='Publish camera frames from the existing local RTSP stream.',
    license='MIT',
    entry_points={'console_scripts': [
        'camera_publisher = eyecar_camera.camera_publisher:main',
    ]},
)
