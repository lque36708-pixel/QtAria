const HOST_NAME = "com.qtaria";

function notifyUser(title, message, isError = false) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.png",
    title: title,
    message: message,
  });
}

function sendToHost(url) {
  let port;
  try {
    port = chrome.runtime.connectNative(HOST_NAME);
  } catch (e) {
    notifyUser("QtAria Error", "Could not connect to QtAria. Run 'python3 -m qtaria install-chrome' first.", true);
    return;
  }

  const timeout = setTimeout(() => {
    notifyUser("QtAria Timeout", "QtAria did not respond. Is it installed correctly?", true);
    try { port.disconnect(); } catch (_) {}
  }, 20000);

  port.onMessage.addListener((msg) => {
    clearTimeout(timeout);
    if (msg.ok) {
      notifyUser("QtAria", "Download sent to QtAria.");
    } else {
      notifyUser("QtAria Error", msg.error || "Unknown error.", true);
    }
    try { port.disconnect(); } catch (_) {}
  });

  port.onDisconnect.addListener(() => {
    clearTimeout(timeout);
    if (chrome.runtime.lastError) {
      notifyUser("QtAria Error", chrome.runtime.lastError.message, true);
    }
  });

  port.postMessage({ url: url });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "qtaria-download",
    title: "Download with QtAria",
    contexts: ["link", "video", "audio"],
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  const url = info.linkUrl || info.srcUrl;
  if (url) {
    sendToHost(url);
  }
});
