# ROS-ноды и прошивка EyeCar

## От Python-файла до ros2 run

ROS 2 Jazzy установлен системно в /opt/ros/jazzy, а исходники EyeCar на Pi
собираются в ~/ros2_ws. Файл setup.py каждого ament_python пакета содержит
console_scripts: слева имя команды для ros2 run, справа Python-модуль и main().
Например, запись

~~~python
'keyboard_teleop = eyecar_teleop.keyboard_teleop:main'
~~~

означает команду ros2 run eyecar_teleop keyboard_teleop. Первое имя —
пакет, второе — executable. ROS-имя ноды внутри кода задаётся отдельно.
Если хочется ros2 run teleop teleop, пакет и запись console_scripts должны
называться teleop.

После изменения Python-кода пакета на Pi:

~~~bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select eyecar_teleop
source install/setup.bash
set -a
source ~/eyecar_web/ros-local.env
set +a
ros2 run eyecar_teleop keyboard_teleop
~~~

Локальный профиль DDS нужен после установки новой версии панели, чтобы команды
по SSH видели сервисы ровера и не публиковались наружу. Если на Pi пока старая
конфигурация, файла ros-local.env ещё нет — эти три строки пропустить.

Топик не создаётся заранее отдельной командой. В rclpy нода вызывает
create_publisher(Twist, '/cmd_vel', 10), затем publisher.publish(message).
Получатель вызывает create_subscription с тем же именем и типом. ROS-граф
показывает доступные топики, пока соответствующие ноды работают:

~~~bash
ros2 topic list
ros2 topic info /cmd_vel
ros2 topic echo /cmd_vel
~~~

Новый пакет можно создать через ros2 pkg create, добавить файл модуля, зависимости
в package.xml, console_scripts в setup.py и затем собрать colcon. Подробный
разбор готовой первой ноды — в EYECAR_WORKFLOW_CHEATSHEET.md.

## Arduino Mega 2560

Прошивка firmware/eyecar_base_controller/eyecar_base_controller.ino компилируется
Arduino CLI независимо от colcon. Текущая цель: arduino:avr:mega:cpu=atmega2560.
Ноут компилирует, Pi передаёт hex на Mega по USB. Сборка текущего скетча
проверена на ноуте; приведённая ниже заливка новой версии ещё не выполнялась.

На ноуте из корня репозитория:

~~~bash
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 \
  --output-dir /tmp/eyecar-fw firmware/eyecar_base_controller
scp /tmp/eyecar-fw/eyecar_base_controller.ino.hex eyecar:/tmp/
~~~

На Pi: сначала убедиться, что колёса вывешены, а нужный serial-порт действительно
принадлежит Arduino. Драйвер держит порт, поэтому перед загрузкой его остановить:

~~~bash
systemctl --user stop eyecar-base.service
arduino-cli upload --verify --fqbn arduino:avr:mega:cpu=atmega2560 \
  --port /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 \
  --input-file /tmp/eyecar_base_controller.ino.hex
systemctl --user start eyecar-base.service
journalctl --user -u eyecar-base.service -n 30 --no-pager
~~~

Ожидаемый ответ контроллера — READY EYECAR_BASE_V1. Если загрузка не прошла,
не запускать телоуправление до проверки порта и восстановления прошивки. Бэкап
штатной Arduino flash/EEPROM и прежних образов есть в проектном каталоге backups/.
