from glob import glob
from pathlib import Path
from setuptools import setup

setup(
    name='eyecar_sim', version='0.1.0', packages=['eyecar_sim'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/eyecar_sim']),
                ('share/eyecar_sim', ['package.xml'])] +
               [(f'share/eyecar_sim/{folder}', [p for p in glob(f'{folder}/*') if Path(p).is_file()])
                for folder in ('config', 'launch', 'worlds', 'protos')],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='mavxa', maintainer_email='mavxa@users.noreply.github.com',
    description='EyeCar Webots simulation', license='MIT',
)
