# Датчики EyeCar

Arduino передаёт `US c1 c2 c3 c4` и `IR a0 a1 a2 a3 a4` по USB serial
на 115200 бод. Единственный владелец порта — `eyecar_base/serial_driver`.
Он публикует два топика типа `std_msgs/msg/UInt16MultiArray`:

| Топик | Порядок data | Значения |
|---|---|---|
| `/eyecar/ultrasonic` | US1, US2, US3, US4 | сантиметры, 0 означает отсутствие эха |
| `/eyecar/infrared` | A0, A1, A2, A3, A4 | сырые ADC 0–1023; в цифровом режиме прошивки 0/1 |

Пары TRIG/ECHO в скетче: 5/6, 7/8, 10/11, 12/13. Это порядок входов,
а не подтверждённые направления расположения датчиков. ИК не пересчитываются
в сантиметры; модель и AO/DO нужно проверить на оборудовании.

На Pi, в новом SSH-сеансе:

```bash
source /opt/eyecar-vision/ros-env.bash
ros2 topic echo /eyecar/ultrasonic
```

В другом терминале:

```bash
source /opt/eyecar-vision/ros-env.bash
ros2 topic echo /eyecar/infrared
```

Частоту можно проверить через `ros2 topic hz /eyecar/ultrasonic` и
`ros2 topic hz /eyecar/infrared`. Данные публикуются только при получении
новой корректной строки от Arduino; старые значения не выдаются за свежие.
Отключение USB прекращает сообщения, а драйвер пытается переподключиться.
Старый скетч без US/IR не выдаёт показаний даже при успешном handshake.

Постоянный процесс запускается `eyecar-base.service`. Сервис уже enabled,
linger для mavxa включён. Топик не хранится отдельно от ноды: пока сервис
работает, publisher существует; после запуска Arduino идут сообщения.

```bash
systemctl --user status eyecar-base.service
journalctl --user -u eyecar-base.service -n 30 --no-pager
```

Для первой проверки использовался drop-in
`~/.config/systemd/user/eyecar-base.service.d/30-sensors-readonly.conf`,
который запускает драйвер с `motion_enabled:=false`. Газ и руление из
`/cmd_vel` игнорируются, передаются только нулевые команды.

12 октября 2026 этот drop-in отключён переименованием в `.conf.disabled`.
Сейчас `motion_enabled=true`, движение разрешено, топики датчиков работают.

Проверяйте каждый ультразвуковой датчик отдельно, ставя предмет перед ним
и наблюдая соответствующий элемент data. Ноль не означает нулевую дистанцию.
Для ИК меняйте расстояние/поверхность перед каждым модулем и наблюдайте
соответствующий вход; постоянный 0 или 1023 сам по себе не доказывает поломку.

Если этот drop-in снова включён и нужно разрешить движение, остановите все teleop
и автономные publishers, затем отключите именно этот drop-in:

```bash
systemctl --user stop eyecar-base.service
mv ~/.config/systemd/user/eyecar-base.service.d/30-sensors-readonly.conf \
   ~/.config/systemd/user/eyecar-base.service.d/30-sensors-readonly.conf.disabled
systemctl --user daemon-reload
systemctl --user start eyecar-base.service
```

Это вернёт прежний запуск с разрешённым движением; оба топика датчиков останутся.
Не запускайте второй serial driver или serial monitor одновременно с сервисом.
