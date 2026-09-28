import './styles.css';

const app = document.querySelector('#app');
const status = document.querySelector('#ros-status');
const demo = import.meta.env.DEV && !new URLSearchParams(location.search).has('live');
const sample = {
  '/cmd_vel': 'geometry_msgs/msg/Twist',
  '/camera/image_raw': 'sensor_msgs/msg/Image',
  '/camera/image_raw/compressed': 'sensor_msgs/msg/CompressedImage',
  '/eyecar/led/state': 'std_msgs/msg/ColorRGBA',
  '/rosout': 'rcl_interfaces/msg/Log',
};
const state = { topics: demo ? sample : {}, socket: null, watching: null, messages: [], connected: false };

function el(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}
function link(label, href, className) {
  const node = el('a', className, label);
  node.href = href;
  node.dataset.route = '';
  return node;
}
function route() {
  const path = decodeURI(location.pathname).replace(/\/+$/, '') || '/';
  if (path === '/') return null;
  if (path === '/cameras/cam') return 'camera';
  if (path === '/cam') return 'standalone-camera';
  return path;
}
function setStatus(label, kind = '') {
  status.className = 'connection ' + kind;
  status.lastElementChild.textContent = label;
}
function send(packet) {
  if (state.socket?.readyState === WebSocket.OPEN) state.socket.send(JSON.stringify(packet));
}
function row(name, type, href, badge = '') {
  const item = link('', href, 'topic-row');
  const left = el('span');
  left.append(el('span', 'topic-name', name), el('span', 'topic-type', type));
  const right = el('span', 'row-right');
  if (badge) right.append(el('span', 'tag', badge));
  right.append(el('span', '', '›'));
  item.append(left, right);
  return item;
}
function section(title, rows) {
  const block = el('section', 'section');
  const heading = el('div', 'section-heading');
  heading.append(el('h2', '', title), el('span', 'count', String(rows.length)));
  const list = el('div', 'topic-list');
  list.append(...(rows.length ? rows : [el('p', 'empty', 'No topics available yet.')]));
  block.append(heading, list);
  return block;
}
function head(name, type) {
  const block = el('div', 'detail-head');
  block.append(el('h1', '', name), el('div', 'detail-type', type));
  return block;
}
function renderHome() {
  const heading = el('div', 'page-heading');
  const title = el('div');
  title.append(el('h1', '', 'Rover overview'), el('p', '', 'Cameras and live ROS topics. The list updates automatically.'));
  heading.append(title);
  const topics = Object.entries(state.topics).sort(([a], [b]) => a.localeCompare(b));
  const isImage = (type) => ['sensor_msgs/msg/Image', 'sensor_msgs/msg/CompressedImage'].includes(type);
  const cameras = [row('/cam', 'WebRTC - MediaMTX', '/cameras/cam/', demo ? 'DEMO' : 'VIDEO')];
  cameras.push(...topics.filter(([, type]) => isImage(type)).map(([name, type]) => row(name, type, name + '/')));
  const others = topics.filter(([, type]) => !isImage(type)).map(([name, type]) => row(name, type, name + '/'));
  app.replaceChildren(heading, section('Cameras', cameras), section('ROS topics', others));
}
function cameraFrame() {
  const frame = el('div', 'video-frame');
  if (demo) {
    frame.append(el('div', 'video-placeholder', 'Demo preview - video appears when connected to the rover'));
  } else {
    const video = document.createElement('iframe');
    video.title = 'EyeCar camera';
    video.allow = 'autoplay; fullscreen';
    video.src = location.protocol + '//' + location.hostname + ':8889/cam?controls=false&muted=true&autoplay=true&playsInline=true';
    frame.append(video);
  }
  return frame;
}
function renderCamera() {
  const actions = el('div', 'detail-actions');
  const standalone = link('Open /cam in a new tab', '/cam/', 'subtle-link');
  standalone.target = '_blank';
  standalone.rel = 'noopener';
  actions.append(standalone);
  if (!demo) {
    const direct = el('a', 'subtle-link', 'Open source stream');
    direct.href = location.protocol + '//' + location.hostname + ':8889/cam';
    direct.target = '_blank';
    direct.rel = 'noopener';
    actions.append(direct);
  }
  app.replaceChildren(link('All topics', '/', 'back'), head('/cam', 'WebRTC - MediaMTX'), cameraFrame(), actions);
}
function renderStandaloneCamera() {
  app.replaceChildren(cameraFrame());
}
function renderTopic(name) {
  const type = state.topics[name];
  const stream = el('div', 'stream');
  if (!state.messages.length) {
    stream.append(el('p', 'empty', demo ? 'Demo preview - no live messages' : 'Waiting for messages…'));
  }
  for (const entry of state.messages) {
    const block = el('div', 'message');
    block.append(el('time', '', entry.time));
    if (entry.msg?.jpeg_base64) {
      const image = document.createElement('img');
      image.className = 'image-preview';
      image.alt = 'ROS topic frame';
      image.src = 'data:image/jpeg;base64,' + entry.msg.jpeg_base64;
      block.append(image);
    } else {
      block.append(el('pre', '', JSON.stringify(entry.msg, null, 2)));
    }
    stream.append(block);
  }
  app.replaceChildren(
    link('All topics', '/', 'back'),
    head(name, type || 'Topic type unavailable'),
    el('p', 'detail-status', demo ? 'Local preview - no live data' : type ? 'Latest messages' : 'Topic currently unavailable'),
    stream,
  );
}
function render() {
  const current = route();
  const standalone = current === 'standalone-camera';
  document.body.classList.toggle('standalone-camera', standalone);
  const watch = current && current !== 'camera' && !standalone ? current : null;
  if (state.watching !== watch) {
    if (state.watching) send({ op: 'unwatch' });
    state.watching = watch;
    state.messages = [];
    if (watch) send({ op: 'watch', topic: watch });
  }
  if (!current) renderHome();
  else if (current === 'camera') renderCamera();
  else if (standalone) renderStandaloneCamera();
  else renderTopic(current);
}
function connect() {
  if (demo) {
    setStatus('ROS: DEMO', 'demo');
    render();
    return;
  }
  setStatus('ROS: connecting');
  const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(scheme + '//' + location.host + '/api/ws');
  state.socket = socket;
  socket.addEventListener('open', () => {
    state.connected = true;
    setStatus('ROS: connected', 'online');
    send({ op: 'list_topics' });
    if (state.watching) send({ op: 'watch', topic: state.watching });
  });
  socket.addEventListener('message', (event) => {
    let packet;
    try { packet = JSON.parse(event.data); } catch { return; }
    if (packet.op === 'topics' && packet.topics && typeof packet.topics === 'object') {
      state.topics = packet.topics;
      if (!['camera', 'standalone-camera'].includes(route())) render();
    } else if (packet.op === 'message' && packet.topic === state.watching) {
      const entry = { time: new Date().toLocaleTimeString('en-GB'), msg: packet.msg };
      if (state.topics[packet.topic] === 'sensor_msgs/msg/CompressedImage') {
        state.messages = [entry];
      } else {
        state.messages.unshift(entry);
        state.messages.length = Math.min(state.messages.length, 30);
      }
      renderTopic(packet.topic);
    }
  });
  socket.addEventListener('close', () => {
    if (state.socket !== socket) return;
    state.connected = false;
    state.topics = {};
    setStatus('ROS: offline');
    if (!['camera', 'standalone-camera'].includes(route())) render();
    setTimeout(connect, 1500);
  });
}
document.addEventListener('click', (event) => {
  const anchor = event.target.closest('a[data-route]');
  if (!anchor || (anchor.target && anchor.target !== '_self') || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
  event.preventDefault();
  history.pushState({}, '', anchor.pathname);
  render();
});
window.addEventListener('popstate', render);
setInterval(() => { if (state.connected) send({ op: 'list_topics' }); }, 3000);
render();
connect();
