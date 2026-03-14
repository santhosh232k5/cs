const notificationBtn = document.getElementById('notificationBtn');
const notificationPanel = document.getElementById('notificationPanel');
const notificationList = document.getElementById('notificationList');
const notificationCount = document.getElementById('notificationCount');
const markReadBtn = document.getElementById('markReadBtn');

function renderNotifications(items = []) {
  if (!notificationList) return;
  notificationList.innerHTML = '';
  if (!items.length) {
    notificationList.innerHTML = '<li class="subtle">No notifications yet.</li>';
    return;
  }

  items.forEach((item) => {
    const li = document.createElement('li');
    li.className = item.is_read ? '' : 'unread';
    li.innerHTML = `<strong>${item.title}</strong><p>${item.message}</p><small>${item.created_at}</small>`;
    notificationList.appendChild(li);
  });
}

async function loadNotifications() {
  if (!notificationBtn) return;
  const response = await fetch('/api/notifications');
  if (!response.ok) return;
  const data = await response.json();
  notificationCount.textContent = data.unread;
  notificationCount.style.display = data.unread > 0 ? 'inline-flex' : 'none';
  renderNotifications(data.items);
}

if (notificationBtn) {
  notificationBtn.addEventListener('click', () => {
    notificationPanel.classList.toggle('hidden');
  });

  markReadBtn.addEventListener('click', async () => {
    await fetch('/api/notifications/read', { method: 'POST' });
    loadNotifications();
  });

  loadNotifications();
  setInterval(loadNotifications, 10000);
}
