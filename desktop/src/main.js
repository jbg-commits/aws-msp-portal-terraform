const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require("electron");
const path = require("path");
const { HIVE_LOGIN_URL } = require("./config");

const ICON_PATH = path.join(__dirname, "..", "build", "icon.ico");
const TRAY_ICON_PATH = path.join(__dirname, "..", "build", "tray.ico");

let mainWindow = null;
let tray = null;
let isQuitting = false;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      if (!mainWindow.isVisible()) mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    createWindow();
    createTray();
  });

  // before-quit fires for EVERY quit path (tray Quit, OS logoff, etc.) before
  // any window's 'close' event -- setting the flag here, not at each quit
  // call site, guarantees the close handler below always sees it correctly.
  app.on("before-quit", () => {
    isQuitting = true;
  });

  // No-op explicitly so Electron's default "quit when all windows closed"
  // never sneaks in and kills the tray-resident app.
  app.on("window-all-closed", () => {});
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "Hive",
    icon: ICON_PATH,
    backgroundColor: "#15120d",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadURL(HIVE_LOGIN_URL);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("close", (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function createTray() {
  tray = new Tray(nativeImage.createFromPath(TRAY_ICON_PATH));
  tray.setToolTip("Hive");

  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: "Open Hive",
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          } else {
            createWindow();
          }
        },
      },
      { type: "separator" },
      { label: "Quit", click: () => app.quit() },
    ])
  );

  tray.on("click", () => {
    if (!mainWindow) return;
    mainWindow.isVisible() ? mainWindow.focus() : mainWindow.show();
  });
}
