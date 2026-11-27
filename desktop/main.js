// Takla Ibrahim for Windows: the same app page as the phone, in its own window.
// The page is served from app://takla/ so its saved data stays in one place between updates.
const { app, BrowserWindow, protocol, net, shell, Menu } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

const HOST = 'takla', ROOT = path.join(__dirname, 'app');
protocol.registerSchemesAsPrivileged([{ scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }]);

if (!app.requestSingleInstanceLock()) app.quit();
let win = null;

function open() {
  win = new BrowserWindow({
    width: 1280, height: 820, minWidth: 380, minHeight: 560,
    title: 'Takla Ibrahim', icon: path.join(ROOT, 'icon-512.png'),
    backgroundColor: '#f3f5f4', autoHideMenuBar: true, show: false,
    webPreferences: { contextIsolation: true, sandbox: true, spellcheck: false }
  });
  win.once('ready-to-show', () => { win.maximize(); win.show(); });
  // WhatsApp, maps and other links open in the normal browser
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^(https?|mailto|tel):/i.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (e, url) => { if (!url.startsWith(`app://${HOST}/`)) { e.preventDefault(); if (/^(https?|mailto|tel):/i.test(url)) shell.openExternal(url); } });
  // Ctrl + / Ctrl - / Ctrl 0 zoom, F5 reload, F11 full screen
  win.webContents.on('before-input-event', (e, k) => {
    if (k.type !== 'keyDown') return;
    const wc = win.webContents, z = wc.getZoomLevel();
    if (k.control && (k.key === '=' || k.key === '+')) { wc.setZoomLevel(z + 0.5); e.preventDefault(); }
    else if (k.control && k.key === '-') { wc.setZoomLevel(z - 0.5); e.preventDefault(); }
    else if (k.control && k.key === '0') { wc.setZoomLevel(0); e.preventDefault(); }
    else if (k.key === 'F5') { wc.reload(); e.preventDefault(); }
    else if (k.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
  });
  win.loadURL(`app://${HOST}/index.html`);
}

app.on('second-instance', () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  protocol.handle('app', req => {
    let p = decodeURIComponent(new URL(req.url).pathname); if (p === '/' || !p) p = '/index.html';
    const f = path.normalize(path.join(ROOT, p));
    if (!f.startsWith(ROOT + path.sep)) return new Response('Not found', { status: 404 });
    return net.fetch(pathToFileURL(f).toString());
  });
  open();
});
app.on('window-all-closed', () => app.quit());
