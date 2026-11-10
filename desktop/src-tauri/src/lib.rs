use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::Manager;

struct BackendProcess(Arc<Mutex<Option<Child>>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_child: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let backend_child_clone = Arc::clone(&backend_child);

    // 1. Spawn openClip python backend if not already running on port 8080
    thread::spawn(move || {
        // Check if port 8080 is answering
        if let Ok(_) = std::net::TcpStream::connect("127.0.0.1:8080") {
            println!("[Tauri] Backend already active on 127.0.0.1:8080");
            return;
        }

        println!("[Tauri] Spawning openClip Python backend...");
        let python_exe = "../clipper/.venv/Scripts/python.exe";
        let child = Command::new(python_exe)
            .args(["-m", "clipper.main", "ui", "--port", "8080"])
            .current_dir("../clipper")
            .spawn();

        match child {
            Ok(process) => {
                println!("[Tauri] Python backend spawned successfully (PID: {})", process.id());
                let mut lock = backend_child_clone.lock().unwrap();
                *lock = Some(process);
            }
            Err(err) => {
                eprintln!("[Tauri] Failed to spawn Python backend: {}", err);
            }
        }
    });

    tauri::Builder::default()
        .manage(BackendProcess(Arc::clone(&backend_child)))
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            
            // Wait briefly for backend ready, then point window to localhost:8080
            thread::spawn(move || {
                for _ in 0..30 {
                    if let Ok(_) = std::net::TcpStream::connect("127.0.0.1:8080") {
                        let _ = window.navigate("http://localhost:8080".parse().unwrap());
                        break;
                    }
                    thread::sleep(Duration::from_millis(500));
                }
            });

            Ok(())
        })
        .on_window_event(move |_window, event| {
            // Clean up python process when user closes main window
            if let tauri::WindowEvent::Destroyed = event {
                if let Ok(mut lock) = backend_child.lock() {
                    if let Some(mut child) = lock.take() {
                        println!("[Tauri] Terminating backend process...");
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
