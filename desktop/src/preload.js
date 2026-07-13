const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("hiveDesktop", {
  getSystemSummary: () => ipcRenderer.invoke("hive:get-system-summary"),
});
