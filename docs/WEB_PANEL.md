# Web-панель EyeCar

Минимальная панель работает непосредственно на Raspberry Pi и доступна любому
устройству в той же сети:

```text
http://172.16.1.182:8080
```

Адрес `172.16.1.182` — текущий DHCP-адрес ровера. Если он изменится, узнать новый
можно в списке клиентов роутера или командой `hostname -I` на Pi.

## Что запущено

```text
браузер :8080 ── web/app.js ── WebSocket :9090 ── /cmd_vel
       │                                      │
       └──── WebRTC :8889/UDP :8189           ▼
                         камера        eyecar_serial_driver
                                               │
                                             Arduino
```

- `eyecar-web.service` раздаёт статические файлы панели на TCP 8080;
- `eyecar-rosbridge.service` даёт панели узкий rosbridge-совместимый WebSocket
  на TCP 9090: публикацию `/cmd_vel` и чтение списка топиков;
- `eyecar-video.service` запускает MediaMTX v1.21.1 и ffmpeg: USB MJPEG
  640x360@30 перекодируется в H.264 около 1 Мбит/с и отдаётся браузеру по WebRTC;
- `eyecar-base.service` держит USB Serial, принимает `/cmd_vel` и отправляет
  команды Arduino Mega.

RTSP слушает только `127.0.0.1:8554`. Наружу открыты TCP 8080, TCP 8889,
TCP 9090 и UDP 8189.

## Управление

- удержание `W`/`S` задаёт газ;
- удержание `A`/`D` задаёт руль независимо от газа;
- `W+A`, `W+D`, `S+A`, `S+D` передают обе оси одновременно;
- `Space`, потеря фокуса вкладки и закрытие WebSocket сбрасывают `/cmd_vel`;
- текущие пределы панели: вперёд `0.18`, назад `-0.25`, руль `±0.85`.

Несколько одновременно открытых панелей сейчас публикуют в один `/cmd_vel`.
Для обычной работы держать управление активным в одной вкладке.

## Управление сервисами

```bash
systemctl --user status \
  eyecar-base eyecar-web eyecar-video eyecar-rosbridge

systemctl --user restart \
  eyecar-base eyecar-web eyecar-video eyecar-rosbridge

journalctl --user -u eyecar-base -f
journalctl --user -u eyecar-video -f
journalctl --user -u eyecar-rosbridge -f
```

Все четыре сервиса уже включены через `systemctl --user enable`. Сейчас у
пользователя `mavxa` выключен linger, поэтому после холодной загрузки они начнут
работать только после его входа. Один раз выполнить:

```bash
sudo loginctl enable-linger mavxa
loginctl show-user mavxa -p Linger
```

Ожидаемый результат второй команды: `Linger=yes`.

## Где лежат файлы

В рабочем проекте:

- `web/` — HTML, CSS и JavaScript панели;
- `ros2_ws/src/eyecar_web/` — ROS 2 WebSocket-мост;
- `deploy/mediamtx.yml` — камера и WebRTC;
- `deploy/systemd-user/` — unit-файлы.

На Raspberry Pi:

- `~/eyecar_web/www/` — раздаваемая панель;
- `~/eyecar_web/mediamtx.yml` — активный конфиг видео;
- `~/.config/systemd/user/eyecar-*.service` — активные unit-файлы;
- `~/ros2_ws/` — собранный ROS 2 workspace.

После изменения ROS-пакета:

```bash
cd ~/ros2_ws
colcon build --symlink-install --packages-select eyecar_web
systemctl --user restart eyecar-rosbridge.service
```

После изменения `web/` скопировать файлы в `~/eyecar_web/www/`; перезапуск
статического сервера не требуется, достаточно обновить страницу.
