const HOST_NAME = "com.qtaria";
let port = null;

function sendToHost(url) {
  if (port) {
    try {
      port.postMessage({ url: url });
      return;
    } catch (e) {
      port = null;
    }
  }

  port = chrome.runtime.connectNative(HOST_NAME);
  port.onMessage.addListener((msg) => {
    if (!msg.ok) {
      console.error("QtAria host error:", msg.error);
    }
    port.disconnect();
    port = null;
  });
  port.onDisconnect.addListener(() => {
    if (chrome.runtime.lastError) {
      console.error("QtAria host disconnected:", chrome.runtime.lastError.message);
    }
    port = null;
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

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const url = info.linkUrl || info.srcUrl;
  if (url) {
    sendToHost(url);
  }
});
