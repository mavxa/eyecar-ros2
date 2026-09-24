# Первый запуск ROS 2 на АЙКАР

Целевая система: Raspberry Pi 4 Model B, Ubuntu Server 24.04 ARM64,
ROS 2 Jazzy. Команды выполняются на Raspberry Pi после первого входа по SSH.

Официальная документация:

- [Установка ROS 2 Jazzy из deb-пакетов](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [Создание Python-пакета](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html)
- [Python publisher/subscriber](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html)
- [Работа с топиками](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html)
- [geometry_msgs/Twist](https://docs.ros.org/en/jazzy/p/geometry_msgs/msg/Twist.html)

## 1. Проверка Raspberry Pi

```bash
uname -m
cat /etc/os-release
```

Ожидается `aarch64` и Ubuntu 24.04 (`noble`). Затем:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

## 2. Установка ROS 2 Jazzy

После повторного входа:

```bash
sudo apt update
sudo apt install -y curl software-properties-common
sudo add-apt-repository -y universe

ROS_APT_SOURCE_VERSION=$(curl -s \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
  | grep -F 'tag_name' | awk -F'"' '{print $4}')

curl -L -o /tmp/ros2-apt-source.deb \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"

sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools
```

Один раз инициализировать `rosdep`:

```bash
sudo rosdep init
rosdep update
```

Если `rosdep init` сообщает, что файл источников уже существует, повторно
инициализировать его не нужно — выполнить только `rosdep update`.

Подключить окружение ROS 2 в текущем терминале и при следующих входах:

```bash
source /opt/ros/jazzy/setup.bash
grep -qxF 'source /opt/ros/jazzy/setup.bash' ~/.bashrc \
  || echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
```

Проверка:

```bash
ros2 --help
ros2 doctor --report
```

## 3. Копирование workspace на Raspberry Pi

На основном компьютере, подставив пользователя и адрес Raspberry Pi:

```bash
rsync -av --exclude build --exclude install --exclude log \
  ~/zed/ros2/eyecar/ros2_ws/ <user>@<raspberry-pi-ip>:~/ros2_ws/
```

## 4. Сборка пакета

На Raspberry Pi:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

Для автоматического подключения workspace:

```bash
grep -qxF 'source ~/ros2_ws/install/setup.bash' ~/.bashrc \
  || echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc
```

## 5. Первые ноды и топик

Основной запуск терминального управления. Команда запускает publisher teleop;
USB-драйвер Arduino Mega постоянно работает через `eyecar-base.service`:

```bash
source ~/ros2_ws/install/setup.bash
ros2 run eyecar_teleop keyboard_teleop
```

Необязательный монитор команд в другом терминале:

```bash
source ~/ros2_ws/install/setup.bash
ros2 run eyecar_teleop cmd_vel_monitor
```

Дополнительная проверка:

```bash
ros2 node list
ros2 topic list
ros2 topic info /cmd_vel
ros2 topic echo /cmd_vel
ros2 topic hz /cmd_vel
```

Ожидаемые основные ноды: `/keyboard_teleop` и `/eyecar_serial_driver`.
`/cmd_vel_monitor` появится только при отдельном запуске монитора. Тип топика
`/cmd_vel`: `geometry_msgs/msg/Twist`.

## 6. Arduino/KvantDuino

Подключить USB-A Raspberry Pi к USB-B/microUSB самого микроконтроллера и проверить:

```bash
lsusb
ls -l /dev/serial/by-id/
```

Если порт есть, добавить пользователя в группу последовательных устройств и
перезайти в систему:

```bash
sudo usermod -aG dialout "$USER"
```

На текущем ровере подтверждена Arduino Mega 2560. Штатный flash, EEPROM и fuse
сохранены в двойном бэкапе. Загружена прошивка
`firmware/eyecar_base_controller`: USB Serial 115200, двигатель S3/D3, руль
S2/D2, нейтраль 1500 мкс и аппаратный watchdog 400 мс.
