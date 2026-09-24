const host = window.location.hostname;
const rosStatus = document.querySelector('#ros-status');
const videoStatus = document.querySelector('#video-status');
const video = document.querySelector('#video');
const videoLink = document.querySelector('#video-link');
const topicsBody = document.querySelector('#topics');
const topicCount = document.querySelector('#topic-count');
const linearValue = document.querySelector('#linear');
const angularValue = document.querySelector('#angular');
const buttons = [...document.querySelectorAll('[data-key]')];

const videoUrl = `http://${host}:8889/cam?controls=false&muted=true&autoplay=true&playsInline=true`;
video.src = videoUrl;
videoLink.href = videoUrl;

const speeds = {
  forward: 0.18,
  reverse: 0.25,
  steering: 0.85,
};

const movementKeys = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD']);
const heldKeys = new Set();
let socket = null;
let reconnectTimer = null;
let topicsTimer = null;
let commandTimer = null;
let lastCommand = { linear: 0, angular: 0 };

function setRosStatus(text, online = false) {
  rosStatus.textContent = text;
  rosStatus.classList.toggle('online', online);
  rosStatus.classList.toggle('offline', !online);
}

function send(payload) {
  if (socket?.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(payload));
  return true;
}

function currentCommand() {
  let linear = 0;
  let angular = 0;

  if (heldKeys.has('KeyW') !== heldKeys.has('KeyS')) {
    linear = heldKeys.has('KeyW') ? speeds.forward : -speeds.reverse;
  }
  if (heldKeys.has('KeyA') !== heldKeys.has('KeyD')) {
    angular = heldKeys.has('KeyA') ? speeds.steering : -speeds.steering;
  }
  return { linear, angular };
}

function renderCommand(command) {
  linearValue.textContent = command.linear.toFixed(3);
  angularValue.textContent = command.angular.toFixed(3);
  buttons.forEach((button) => {
    button.classList.toggle('active', heldKeys.has(button.dataset.key));
  });
}

function publishCommand(force = false) {
  const command = currentCommand();
  const changed = command.linear !== lastCommand.linear
    || command.angular !== lastCommand.angular;
  if (!force && !changed && heldKeys.size === 0) return;

  send({
    op: 'publish',
    topic: '/cmd_vel',
    msg: {
      linear: { x: command.linear, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: command.angular },
    },
  });
  lastCommand = command;
  renderCommand(command);
}

function stop() {
  heldKeys.clear();
  publishCommand(true);
}

function requestTopics() {
  send({
    op: 'call_service',
    id: 'eyecar-topics',
    service: '/rosapi/topics',
    type: 'rosapi_msgs/srv/Topics',
    args: {},
  });
}

function renderTopics(topics, types) {
  const entries = topics.map((name, index) => ({
    name,
    type: types[index] || 'unknown',
  })).sort((left, right) => left.name.localeCompare(right.name));

  topicsBody.replaceChildren(...entries.map(({ name, type }) => {
    const row = document.createElement('tr');
    const nameCell = document.createElement('td');
    const typeCell = document.createElement('td');
    nameCell.textContent = name;
    typeCell.textContent = type;
    row.append(nameCell, typeCell);
    return row;
  }));
  topicCount.textContent = String(entries.length);
}

function connectRos() {
  clearTimeout(reconnectTimer);
  setRosStatus('ROS: подключение');
  socket = new WebSocket(`ws://${host}:9090`);

  socket.addEventListener('open', () => {
    setRosStatus('ROS: подключено', true);
    send({
      op: 'advertise',
      id: 'eyecar-cmd-vel',
      topic: '/cmd_vel',
      type: 'geometry_msgs/msg/Twist',
    });
    requestTopics();
    clearInterval(topicsTimer);
    topicsTimer = setInterval(requestTopics, 3000);
    clearInterval(commandTimer);
    commandTimer = setInterval(() => publishCommand(false), 50);
  });

  socket.addEventListener('message', (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    if (message.op === 'service_response' && message.id === 'eyecar-topics') {
      const values = message.values || {};
      renderTopics(values.topics || [], values.types || []);
    }
  });

  socket.addEventListener('error', () => {
    setRosStatus('ROS: ошибка');
  });

  socket.addEventListener('close', () => {
    setRosStatus('ROS: нет связи');
    clearInterval(topicsTimer);
    clearInterval(commandTimer);
    stop();
    reconnectTimer = setTimeout(connectRos, 1500);
  });
}

function press(code) {
  if (code === 'Space') {
    stop();
    return;
  }
  if (!movementKeys.has(code)) return;
  heldKeys.add(code);
  publishCommand(true);
}

function release(code) {
  if (!movementKeys.has(code)) return;
  heldKeys.delete(code);
  publishCommand(true);
}

window.addEventListener('keydown', (event) => {
  if (!movementKeys.has(event.code) && event.code !== 'Space') return;
  event.preventDefault();
  press(event.code);
});

window.addEventListener('keyup', (event) => {
  if (!movementKeys.has(event.code) && event.code !== 'Space') return;
  event.preventDefault();
  release(event.code);
});

window.addEventListener('blur', stop);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stop();
});
window.addEventListener('beforeunload', stop);

buttons.forEach((button) => {
  const code = button.dataset.key;
  button.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    press(code);
  });
  button.addEventListener('pointerup', () => release(code));
  button.addEventListener('pointercancel', () => release(code));
});

video.addEventListener('load', () => {
  videoStatus.textContent = 'Video: подключено';
  videoStatus.classList.add('online');
});

connectRos();
