# Панель EyeCar

Главная страница после развёртывания — http://eyecar.local/ или http://<IP Pi>/.
Она показывает камеры и доступные ROS-топики. Адрес топика открывает последние
сообщения и тип; /cameras/cam/ открывает WebRTC-видео и ссылку на отдельный
адрес /cam/. Он занимает всю вкладку без интерфейса панели: вкладку можно
перенести на второй монитор и развернуть через F11. Подписи интерфейса — на
английском. Панель не отправляет
команды роботу. Управление остаётся в SSH: ros2 run eyecar_teleop keyboard_teleop.

28 сентября 2026 панель развёрнута на Pi: Nginx слушает :80, старый сервер
:8080 выключен, WebSocket-мост слушает только 127.0.0.1:9090. На Pi проверены
список живых топиков, чтение JPEG через мост и около 9,5 кадров/с в
`/camera/image_raw`. WebRTC-страница MediaMTX отвечает по :8889; воспроизведение
в браузере на каждом клиентском устройстве отдельно не проверялось.

## Локальное редактирование

На ноуте:

~~~bash
cd /home/mavxa/zed/ros2/eyecar/eyecar-ros2/web
bun install
bun run dev
~~~

Открыть http://127.0.0.1:5173/. Без Pi показывается явно обозначенный
демо-список. После изменения HTML/CSS/JS Vite обновляет страницу. Для подключения
к живому мосту на том же хосте можно открыть /?live=1. Сборка: bun run build,
результат в web/dist/. На Pi ставятся только собранные файлы, Bun/Vite там не
нужны. Исходники: web/index.html, web/styles.css, web/app.js.

## Схема

~~~text
браузер :80 -> Nginx -> статика web/dist
                    -> /api/ws -> 127.0.0.1:9090 -> список/подписка ROS
                    -> WebRTC :8889/UDP :8189 -> MediaMTX
USB камера -> ffmpeg -> MediaMTX -> локальный RTSP :8554 -> eyecar_camera
                                                        -> /camera/image_raw
                                                        -> /camera/image_raw/compressed
SSH teleop -> /cmd_vel -> eyecar_base -> Arduino
~~~

WebSocket-мост принимает только list_topics, watch, unwatch; неизвестные
операции возвращают ошибку. Список топиков обновляется раз в 3 с, сообщения
ограничены 10 Гц на топик и 30 последними в браузере. Сырой Image в текстовом
просмотрщике заменён метаданными, JPEG из CompressedImage можно посмотреть.

ROS-поток берётся из существующего RTSP, поэтому USB-камеру второй процесс не
открывает. Нода публикует максимум 10 кадров/с, исходный bgr8 и JPEG качества
70. 8 ГБ ОЗУ достаточно для такого буфера, но нагрузку на CPU, задержку и
потерю кадров нужно измерить на Pi перед постоянным включением.

## Установка на Pi

Сначала проверить, что на Pi установлены nginx, python3-opencv, ROS 2 Jazzy
и ros-jazzy-rmw-cyclonedds-cpp, есть права на установку Nginx, а актуальный
репозиторий скопирован в ~/eyecar-ros2. Сохранить активные конфиги до замены.
Для всех команд ROS на Pi нужен один и тот же локальный профиль DDS.

~~~bash
cd ~/eyecar-ros2
sudo apt install nginx python3-opencv ros-jazzy-rmw-cyclonedds-cpp
sudo apt install avahi-daemon
sudo hostnamectl set-hostname eyecar
sudo systemctl enable --now avahi-daemon
mkdir -p ~/eyecar_web ~/.config/systemd/user
cp deploy/ros-local.env ~/eyecar_web/
cp deploy/cyclonedds-loopback.xml ~/eyecar_web/
grep -qxF 'set -a; source /home/mavxa/eyecar_web/ros-local.env; set +a' ~/.bashrc \
  || echo 'set -a; source /home/mavxa/eyecar_web/ros-local.env; set +a' >> ~/.bashrc
cp deploy/systemd-user/{eyecar-base,eyecar-rosbridge,eyecar-camera}.service ~/.config/systemd/user/
sudo cp deploy/systemd/eyecar-led.service /etc/systemd/system/
sudo cp deploy/nginx/eyecar.conf /etc/nginx/sites-available/eyecar
sudo ln -s /etc/nginx/sites-available/eyecar /etc/nginx/sites-enabled/eyecar
sudo unlink /etc/nginx/sites-enabled/default  # конфиг в sites-available сохраняется
sudo nginx -t
cp -a ros2_ws/src/eyecar_web ros2_ws/src/eyecar_camera ~/ros2_ws/src/
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select eyecar_web eyecar_camera
# Копировать с ноутбука содержимое web/dist/ в /var/www/eyecar/
systemctl --user daemon-reload
sudo systemctl daemon-reload
systemctl --user disable --now eyecar-web.service
systemctl --user restart eyecar-base eyecar-rosbridge eyecar-video
systemctl --user enable --now eyecar-camera
sudo systemctl restart eyecar-led nginx
~~~

На Pi Bun не требуется: передать готовый web/dist/ с ноутбука. При первой
установке eyecar-rosbridge будет слушать только 127.0.0.1:9090; Nginx даёт
браузеру /api/ws. Порт 8080 старой панели закрывается после остановки сервиса.
MediaMTX остаётся доступен на :8889/UDP :8189, поэтому камеру смогут смотреть
участники той же сети.

Перед переключением DDS проверить работающие ROS-процессы и CLI; затем
перезапустить ROS daemon, если он был запущен со старым окружением. В SSH:

~~~bash
set -a
source ~/eyecar_web/ros-local.env
set +a
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 daemon stop
ros2 topic list
ros2 run eyecar_teleop keyboard_teleop
~~~

Проверить на Pi `ros2 topic hz /camera/image_raw --spin-time 3`,
`ros2 topic hz /camera/image_raw/compressed --spin-time 3`, `top`,
затем открыть /,
/cmd_vel/, /cameras/cam/, /cam/ на телефоне и ноуте. Проверить прямой переход по
вложенному URL и работу после перезагрузки. С другого компьютера с ROS убедиться,
что узлы Pi не обнаруживаются. Если обнаруживаются, не считать DDS изоляцию
готовой: проверить переменные всех сервисов и интерфейс `lo` в Cyclone DDS, а также
остановить узлы, запущенные вручную без локального профиля.

eyecar.local зависит от работающего mDNS/Avahi у Pi и клиента; по IP панель
должна открываться независимо от него. Профиль DDS ограничивает процессы,
запущенные с этим окружением; другие ROS-процессы без профиля могут остаться
доступными через сеть. Это следует проверить на самом ровере.

Полезные журналы:

~~~bash
systemctl --user status eyecar-base eyecar-rosbridge eyecar-video eyecar-camera
journalctl --user -u eyecar-camera -n 50 --no-pager
journalctl --user -u eyecar-rosbridge -n 50 --no-pager
sudo nginx -t
~~~
