use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use tauri::{Emitter, Window};

fn validate_repo_root(path: PathBuf) -> Result<PathBuf, String> {
    let bridge_script = path.join("scripts").join("workbench_bridge.py");
    if bridge_script.is_file() {
        Ok(path)
    } else {
        Err(format!(
            "无法定位发布引擎目录：缺少 {}",
            bridge_script.display()
        ))
    }
}

fn resolve_repo_root_from(manifest_dir: PathBuf, explicit_root: Option<PathBuf>) -> Result<PathBuf, String> {
    if let Some(root) = explicit_root {
        return validate_repo_root(root);
    }
    manifest_dir
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or_else(|| "无法推断仓库根目录".to_string())
        .and_then(validate_repo_root)
}

fn repo_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let explicit_root = std::env::var("ORDO_REPO_ROOT").ok().map(PathBuf::from);
    resolve_repo_root_from(manifest_dir, explicit_root)
}

fn python_executable() -> String {
    std::env::var("ORDO_PYTHON").unwrap_or_else(|_| "python3".to_string())
}

fn bridge_script_path() -> Result<PathBuf, String> {
    Ok(repo_root()?.join("scripts").join("workbench_bridge.py"))
}

fn run_bridge_once(payload: Value) -> Result<Value, String> {
    let root = repo_root()?;
    let script = bridge_script_path()?;
    let request = serde_json::to_vec(&payload).map_err(|err| err.to_string())?;
    let mut child = Command::new(python_executable())
        .arg(script)
        .current_dir(root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("启动 Python bridge 失败: {err}"))?;
    child
        .stdin
        .as_mut()
        .ok_or_else(|| "无法打开 Python bridge stdin".to_string())?
        .write_all(&request)
        .map_err(|err| format!("写入 Python bridge 请求失败: {err}"))?;
    let output = child
        .wait_with_output()
        .map_err(|err| format!("等待 Python bridge 结果失败: {err}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() {
            format!("Python bridge 失败，退出码 {:?}", output.status.code())
        } else {
            stderr
        });
    }
    serde_json::from_slice(&output.stdout).map_err(|err| format!("解析 Python bridge JSON 失败: {err}"))
}

#[tauri::command]
fn bridge_request(payload: Value) -> Result<Value, String> {
    run_bridge_once(payload)
}

#[tauri::command]
fn run_publish_job_stream(window: Window, plan: Value) -> Result<Value, String> {
    let root = repo_root()?;
    let script = bridge_script_path()?;
    let request = serde_json::to_vec(&json!({
        "command": "run_publish_job_stream",
        "plan": plan,
    }))
    .map_err(|err| err.to_string())?;
    let mut child = Command::new(python_executable())
        .arg(script)
        .current_dir(root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("启动发布任务失败: {err}"))?;
    child
        .stdin
        .as_mut()
        .ok_or_else(|| "无法打开发布任务 stdin".to_string())?
        .write_all(&request)
        .map_err(|err| format!("写入发布任务请求失败: {err}"))?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "无法读取发布任务 stdout".to_string())?;
    let mut reader = BufReader::new(stdout);
    let mut line = String::new();
    let mut final_payload: Option<Value> = None;

    loop {
        line.clear();
        let bytes = reader
            .read_line(&mut line)
            .map_err(|err| format!("读取发布事件失败: {err}"))?;
        if bytes == 0 {
            break;
        }
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let event: Value =
            serde_json::from_str(trimmed).map_err(|err| format!("解析发布事件失败: {err}"))?;
        if event.get("type").and_then(Value::as_str) == Some("command_result") {
            final_payload = event.get("payload").cloned();
        } else {
            window
                .emit("publish-event", &event)
                .map_err(|err| format!("发送桌面发布事件失败: {err}"))?;
        }
    }

    let output = child
        .wait_with_output()
        .map_err(|err| format!("等待发布任务退出失败: {err}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if stderr.is_empty() {
            format!("发布任务失败，退出码 {:?}", output.status.code())
        } else {
            stderr
        });
    }

    final_payload.ok_or_else(|| "发布任务未返回最终结果".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![bridge_request, run_publish_job_stream])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::{resolve_repo_root_from, validate_repo_root};
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_path(name: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time")
            .as_nanos();
        std::env::temp_dir().join(format!("ordo-desktop-{name}-{nonce}"))
    }

    #[test]
    fn validate_repo_root_accepts_directory_with_bridge_script() {
        let root = temp_path("valid-root");
        fs::create_dir_all(root.join("scripts")).expect("create scripts dir");
        fs::write(root.join("scripts").join("workbench_bridge.py"), "print('ok')").expect("write bridge");

        let validated = validate_repo_root(root.clone()).expect("valid repo root");

        assert_eq!(validated, root);
    }

    #[test]
    fn resolve_repo_root_prefers_explicit_override() {
        let override_root = temp_path("override-root");
        fs::create_dir_all(override_root.join("scripts")).expect("create scripts dir");
        fs::write(
            override_root.join("scripts").join("workbench_bridge.py"),
            "print('ok')",
        )
        .expect("write bridge");

        let resolved = resolve_repo_root_from(
            PathBuf::from("/tmp/unused/desktop/src-tauri"),
            Some(override_root.clone()),
        )
        .expect("resolve repo root");

        assert_eq!(resolved, override_root);
    }
}
