# Практика: свой детектор объектов для EyeCar

**Задача:** собрать и разметить датасет, обучить YOLO11n, проверить модель с
USB-камерой на ноутбуке и написать ROS 2-ноду для ровера. При обнаружении
объекта ровер должен менять цвет LED. Короткий проезд можно сделать дополнительно.

Возьми один класс, например `cup` — кружка. Можно выбрать другой доступный
предмет, но согласуй название класса до разметки. Для первого варианта достаточно
одного класса и одной реакции. Распознаём объект нейросетью; OpenCV нужен для
получения, декодирования и показа кадров.

Готового алгоритма ноды здесь нет. Примеры ниже показывают отдельные операции;
связать их в работающую программу нужно самостоятельно.

## 1. Собери и разметь датасет

Создай в Roboflow проект типа **Object Detection**. Сними примерно 50-80
разных кадров, желательно той камерой, которая будет стоять на ровере.
Это стартовый объём для упражнения, а не гарантия качества модели.

- Меняй расстояние, ракурс, фон и освещение. Включи кадры с частично закрытым предметом.
- Добавь кадры без целевого объекта, в том числе с похожими предметами.
- Размечай прямоугольником каждый видимый объект выбранного класса.
- Используй одно написание класса: `cup`, без вариантов `Cup` и `cups`.
- Раздели данные примерно на 70% train, 20% valid и 10% test.

Соседние кадры одного видео не раскладывай случайно по разным частям:
почти одинаковые изображения дадут завышенную оценку. Отдели съёмочные сцены
для проверки заранее. Аугментации применяй только к train.

Сгенерируй версию датасета и скачай ZIP в формате **Ultralytics YOLO detection**,
совместимом с YOLO11. В интерфейсе Roboflow он может называться YOLOv8.
Нужны `data.yaml`, изображения и текстовые аннотации, а не экспорт для классификации.
API-ключ для скачивания ZIP вручную не нужен.

После распаковки проверь пути `train`, `val` и `test` в `data.yaml` и список
`names`. Открой несколько картинок с разметкой и убедись, что рамки стоят верно.
Формат датасета описан в [русской документации Ultralytics](https://docs.ultralytics.com/ru/datasets/detect/).

**Результат этапа:** ссылка на проект/версию Roboflow, `data.yaml` и датасет,
из которого можно повторить обучение.

## 2. Обучи модель на ноутбуке

Сохрани отдельные файлы `train.py`, `camera_test.py` и `detector_node.py`.
Большой датасет и веса не нужно класть в Git вместе с кодом.

Для обычного Python на ноутбуке можно подготовить окружение:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install ultralytics opencv-python
```

Установи пакет с GUI, а не `opencv-python-headless`, если собираешься пользоваться
`cv2.imshow`. Этот шаг не ставит ROS 2; для ROS-ноды ниже используется Jazzy.
Версию Ultralytics для обучения согласуй с наставником: желательно использовать
ту же версию, что в общем окружении Pi. Общее окружение ровера самостоятельно
не обновляй ради открытия весов, созданных более новой версией.

Минимальный пример обучения в `train.py`:

```python
from ultralytics import YOLO


def main():
    model = YOLO("yolo11n.pt")
    model.train(data="dataset/data.yaml", epochs=50, imgsz=640,
                device="cpu", project="runs", name="cup_yolo11n")


if __name__ == "__main__":
    main()
```

Запуск: `.venv/bin/python train.py`. Путь к датасету замени своим.
`yolo11n.pt` — предобученные веса: Ultralytics скачает их при первом запуске,
если файл отсутствует и есть интернет. `yolo11n.yaml` описывает архитектуру
для обучения с нуля; в этом задании используй `.pt`.
См. [YOLO11](https://docs.ultralytics.com/ru/models/yolo11/) и
[обучение](https://docs.ultralytics.com/ru/modes/train/).

На CPU обучение может занять долгое время. Если есть поддерживаемая NVIDIA GPU,
настроенный PyTorch с CUDA и `torch.cuda.is_available()` возвращает `True`,
можно заменить `device="cpu"` на `device=0`. Сначала допустим пробный запуск
на 3 эпохи, чтобы проверить пути; это ещё не готовая модель.

Сохрани **`weights/best.pt`** из каталога завершённого запуска. При повторных
запусках имя каталога может получить числовой суффикс — смотри путь в консоли.
Запиши число эпох, размер изображения, версию Ultralytics и полученный mAP50
на valid. Тестовую выборку оставь для итоговой проверки.

## 3. Проверь камеру и модель на ноутбуке

Подключи USB-камеру ровера к ноутбуку. Сначала получи обычную картинку, без ROS
и нейросети. Не запускай несколько программ захвата одной камеры одновременно.

Короткий пример OpenCV:

```python
import cv2

cap = cv2.VideoCapture(0)
try:
    if not cap.isOpened():
        raise RuntimeError("Camera is not available")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("Camera", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
```

Индекс `0` может оказаться встроенной веб-камерой. Выбери индекс своей USB-камеры;
в Linux также можно передать путь вроде `/dev/video2`.
Функции разобраны в [официальном уроке OpenCV](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html).

Затем самостоятельно добавь в `camera_test.py` обработку кадров моделью.
Пример предсказания **для одного изображения**, отдельно от видеозахвата:

```python
from ultralytics import YOLO

model = YOLO("best.pt")
result = model.predict("test.jpg", conf=0.5, imgsz=416, device="cpu")[0]
for box in result.boxes:
    label = result.names[int(box.cls.item())]
    print(label, float(box.conf.item()), box.xyxy[0].tolist())
result.save(filename="test_result.jpg")
```

В `predict` можно передать и `frame`, полученный OpenCV. `result.plot()` возвращает
изображение с рамками. Модель загружай один раз, а не на каждом кадре.
Справка: [предсказания и Results](https://docs.ultralytics.com/ru/modes/predict/).

В рабочем просмотре должны быть видны рамка, название класса и confidence.
В консоль выводи класс, confidence и координаты рамки. Проверь новые сцены,
которые не использовались в обучении: объект близко/далеко, другой фон,
пустой кадр и похожий посторонний предмет. Запиши примеры ошибок и примерный FPS.

**Результат этапа:** рабочий `camera_test.py`, проверенный `best.pt` и короткая
запись экрана с детектом. Модель должна находить предмет и после смены фона.

## 4. Оформи детектор как ROS 2-ноду на ноутбуке

Теперь напиши `detector_node.py` на `rclpy`. Пока камера подключена к ноутбуку,
кадры можно получать напрямую через OpenCV. Нода должна публиковать сведения
о найденных объектах в **`/practice/detections`**, тип `std_msgs/msg/String`.
Содержимое строки — JSON, например:

```json
{"detections": [{"class": "cup", "confidence": 0.87, "bbox_xyxy": [20, 30, 180, 220]}]}
```

Если объектов нет, публикуй `{"detections": []}`. Координаты рамок — в пикселях
исходного кадра. Начни с порога confidence `0.5`; при изменении запиши выбранное
значение. Confidence — оценка модели, а не гарантия правильного ответа.

Ниже только независимый пример ROS-publisher. Это не заготовка детектора:

```python
import rclpy
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node("hello_example")
publisher = node.create_publisher(String, "/practice/hello", 10)
timer = node.create_timer(
    1.0, lambda: publisher.publish(String(data="Hello")))
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
finally:
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
```

Нода запускается обычным Python в окружении, где доступны `rclpy`, OpenCV и
Ultralytics. Для файла в `scripts/` сборка `colcon` не требуется.
Используй имеющийся [Jazzy devcontainer](../docs/DEVELOPMENT.md), а не
`pip install rclpy`. Обычная `.venv` из предыдущего этапа ROS не содержит.

Если запускаешь захват в Linux-контейнере, передай ему именно устройство камеры.
Пример с хоста из корня репозитория, **путь замени своим**:

```bash
docker compose run --rm --no-deps --device /dev/video2:/dev/video2 ros2 bash
```

В таком контейнере `VideoCapture` должен открывать `/dev/video2`. Нужны права
чтения устройства и доступ к графической сессии для `imshow`. Для ROS-совместимого
Python-окружения внутри контейнера используй `venv --system-site-packages` после
`source /opt/ros/jazzy/setup.bash` и установи туда Ultralytics/OpenCV. Не переноси
готовую `.venv` между ноутбуком и ARM64 Pi. Если с окном есть проблема, сначала
проверь публикацию детектов без окна.

Из второго терминала с тем же ROS-доменом проверь:

```bash
ros2 node list
ros2 topic info /practice/detections
ros2 topic echo /practice/detections
```

**Результат этапа:** нода на ноутбуке публикует реальные детекты с камеры;
при убранном объекте массив становится пустым.

## 5. Перенеси модель и ноду на EyeCar

Работай на Pi под пользователем **`griftf`**. Файл ноды положи в
`/home/griftf/scripts/practice_detector.py`, модель — в
**`/opt/eyecar-models/cup/best.pt`**. Для другого класса выбери своё имя подкаталога.
Каталог моделей общий, но модель этого задания не должна перезаписывать чужие веса.

Наставник один раз создаёт каталог для модели:

```bash
sudo install -d -o griftf -g users -m 0755 /opt/eyecar-models/cup
```

Под `griftf` создай `~/scripts`. Передай `.py` и проверенный `best.pt` через SCP,
затем положи модель в указанный каталог. Датасет и окружение с ноутбука копировать
не нужно. Это новый путь для задания; старые примеры проекта могут использовать
`/opt/eyecar-vision/models/`.

На Pi уже предусмотрено общее окружение `/opt/eyecar-vision/venv`.
Проверь импорты и запускай ноду его интерпретатором:

```bash
source /opt/eyecar-vision/ros-env.bash
/opt/eyecar-vision/venv/bin/python -c 'import rclpy, cv2, ultralytics'
/opt/eyecar-vision/venv/bin/python ~/scripts/practice_detector.py
```

Если общего окружения или файла настройки нет, обратись к наставнику:
его установка описана в [VISION.md](../docs/VISION.md). Не ставь зависимости
через системный `sudo pip`. Для первого запуска на Pi оставь модель `.pt`,
CPU и `imgsz=416`; экспорт в ONNX в это задание не входит.

Камеру верни на ровер. **На Pi получай изображение из готового ROS-топика**
`/camera/image_raw/compressed`, тип `sensor_msgs/msg/CompressedImage`,
с `qos_profile_sensor_data`. Не открывай `/dev/video0` вторым процессом:
камеру уже захватывает видеосервис. Измени источник кадров в своей ноде,
сохранив модель и формат детектов.

Отдельная операция декодирования JPEG, где `msg` — полученное сообщение:

```python
import cv2
import numpy as np

frame = cv2.imdecode(np.frombuffer(msg.data, dtype=np.uint8), cv2.IMREAD_COLOR)
```

Дальше работать нужно с новым `frame`; старые кадры не должны накапливаться
в очереди, если инференс медленный. Сначала добейся детектов на Pi без реакции
ровера. Измерь FPS заново: скорость на ноутбуке не равна скорости на Pi.

## 6. Добавь реакцию ровера самостоятельно

**Основной вариант — LED.** Когда в кадре есть целевой класс с confidence
не ниже выбранного порога, подсветка зелёная; когда объекта нет — синяя.
Используй `/eyecar/led/color`, тип `std_msgs/msg/ColorRGBA`.
Компоненты `r`, `g`, `b` задаются от 0.0 до 1.0, `a` оставь 1.0.
Существующую ноду LED и её прошивку менять не требуется.

**Дополнительный вариант — короткий проезд.** При подтверждённом детекте
один раз проехать вперёд не более 0.5 секунды и остановиться. Пока предмет
остаётся в кадре, новые кадры не должны запускать следующие проезды.
Повторный запуск разрешается только после исчезновения и нового появления предмета.

Для движения используется `/cmd_vel`, тип `geometry_msgs/msg/Twist`.
Команды подавай регулярно, например 20 Гц, а после завершения действия отправь
нулевую команду. Не блокируй обработку ROS долгим `sleep` и не привязывай
частоту команд к медленному инференсу. В текущем драйвере EyeCar `linear.x`
масштабируется в газ, а `angular.z` в руление: это не откалиброванные м/с и рад/с.
Значение газа для короткого теста согласуй с наставником.

Проверку движения сначала проводи с вывешенными колёсами, без запущенного teleop
и других издателей `/cmd_vel`. Потеря камеры или завершение программы не должны
оставлять ненулевую команду; предусмотренный драйвером timeout не заменяет
явную остановку в твоей программе.

Не используй готовую миссию из репозитория как своё решение. Нужно самому
связать получение кадра, детекцию, публикацию результатов и выбранную реакцию.

## Что показать при сдаче

- Проект Roboflow, состав выборок и несколько примеров разметки.
- `train.py`, параметры обучения, mAP50 и проверенный `best.pt`.
- Детект с USB-камеры на ноутбуке: рамки, названия, confidence и лог координат.
- Свою ROS-ноду и вывод `/practice/detections`, в том числе пустой массив.
- Ту же модель на Pi под `griftf` и работу реакции LED. Проезд — по желанию.
- Короткое видео и заметку: что срабатывает, где модель ошибается, какой FPS
  получился на ноутбуке и на Pi.

Для проверки вместе с наставником сделай 10 показов объекта и 10 проверок
без него, на новом фоне. Запиши число верных срабатываний и ложных детектов.
Это небольшая проверка упражнения, а не замена оценки на test-выборке.

На разборе объясни, чем отличаются обучение и инференс, `best.pt` и
`yolo11n.pt`, почему нужен отдельный test, как создаётся publisher и откуда
берутся кадры на Pi. Уметь объяснить своё решение важнее количества строк.

## Документация: что читать

У Ultralytics есть официальные русские страницы. Для OpenCV и `rclpy` здесь
приведены официальные английские уроки: проверенного русского перевода этих
разделов в подборке нет. Их можно читать с переводом браузера; имена API
оставляй как в оригинале. В общих примерах Ultralytics могут встречаться
более новые модели; для этого задания сохраняй `yolo11n.pt`.

| Тема | Ссылка | Что найти |
| --- | --- | --- |
| Установка Ultralytics, RU | [Quickstart](https://docs.ultralytics.com/ru/quickstart/) | Установка, Python API |
| YOLO11, RU | [Модель YOLO11](https://docs.ultralytics.com/ru/models/yolo11/) | Предобученные веса и варианты n/s/m |
| Roboflow, RU | [Руководство Ultralytics](https://docs.ultralytics.com/ru/integrations/roboflow/) | Разметка и экспорт |
| Roboflow, EN | [Export a Dataset Version](https://docs.roboflow.com/datasets/exporting-data) | Скачивание версии датасета в ZIP |
| Датасет, RU | [Формат detection](https://docs.ultralytics.com/ru/datasets/detect/) | `data.yaml`, классы, формат рамок |
| Обучение, RU | [Train](https://docs.ultralytics.com/ru/modes/train/) | `data`, `epochs`, `imgsz`, `device` |
| Инференс и OpenCV-кадры, RU | [Predict](https://docs.ultralytics.com/ru/modes/predict/) | Вход `np.ndarray` BGR, `conf`, `boxes`, `plot()` |
| Python API, RU | [Использование Python](https://docs.ultralytics.com/ru/usage/python/) | `YOLO`, `train`, `predict`, `val` |
| OpenCV: камера, EN | [Getting Started with Videos](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) | `VideoCapture`, `read`, `imshow`, `waitKey`, `release` |
| OpenCV: основы, EN | [OpenCV-Python Tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html) | Изображения, массивы, цветовые пространства |
| ROS 2 Jazzy: publisher/subscriber, EN | [Python tutorial](https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html) | Создание ноды, publisher, subscription, spin |
| rclpy: Node, EN | [API](https://docs.ros.org/en/jazzy/p/rclpy/api/node.html) | `create_publisher`, `create_subscription`, `create_timer` |
| ROS 2: QoS, EN | [QoS settings](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) | Совместимость подписки с камерой |
| ROS: сжатое изображение, EN | [CompressedImage](https://docs.ros.org/en/jazzy/p/sensor_msgs/msg/CompressedImage.html) | `header`, `format`, `data` |
| EyeCar | [Workflow](../docs/EYECAR_WORKFLOW_CHEATSHEET.md), [vision](../docs/VISION.md), [LED](../ros2_ws/src/eyecar_led/README.md) | Окружение, запуск скрипта, интерфейсы ровера |

Начни с урока OpenCV про камеру и страниц YOLO11 / Train / Predict.
К `rclpy` переходи после рабочей проверки модели на ноутбуке. Если сайт ROS
не открывается из-за защиты, текст учебника есть в
[официальном репозитории документации](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.rst).
