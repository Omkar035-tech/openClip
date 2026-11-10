const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow = null;
let pythonProcess = null;

const PORT = 8080;
const SERVER_URL = `http://localhost:${PORT}`;

function isServerReady(callback) {
  const req = http.get(SERVER_URL, (res) => {
    callback(true);
  });
  req.on('error', () => {
    callback(false);
  });
  req.end();
}

function startBackend() {
  isServerReady((ready) => {
    if (ready) {
      console.log('[Desktop] Backend is already running on port ' + PORT);
      createWindow();
      return;
    }

    console.log('[Desktop] Launching openClip Python backend server...');
    const pythonExe = path.resolve(__dirname, '../clipper/.venv/Scripts/python.exe');
    const cwd = path.resolve(__dirname, '../clipper');

    pythonProcess = spawn(pythonExe, ['-m', 'clipper.main', 'ui', '--port', String(PORT)], {
      cwd: cwd,
      stdio: 'pipe',
      detached: false
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`[Python]: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Err]: ${data}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Desktop] Python process exited with code ${code}`);
    });

    // Wait for server ready, then open window
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      isServerReady((isReady) => {
        if (isReady) {
          clearInterval(interval);
          createWindow();
        } else if (attempts > 30) {
          clearInterval(interval);
          dialog.showErrorBox(
            'Backend Startup Error',
            'Could not start openClip Python server within 30 seconds. Please check that port 8080 is free.'
          );
        }
      });
    }, 1000);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'openClip Studio - AI Video Editor (Desktop)',
    backgroundColor: '#0b0f19',
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadURL(SERVER_URL);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    console.log('[Desktop] Shutting down Python backend process...');
    try {
      process.kill(pythonProcess.pid);
    } catch (e) {
      // process already dead
    }
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
