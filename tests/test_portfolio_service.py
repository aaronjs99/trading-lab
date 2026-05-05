from pathlib import Path

from trading_lab.portfolio import service


def test_service_defaults_use_lab_port():
    assert service.DEFAULT_HOST == "127.0.0.1"
    assert service.DEFAULT_PORT == 811
    assert service.service_url() == "http://127.0.0.1:811/"


def test_service_status_handles_missing_pid_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(service, "RUNTIME_DIR", Path("data/runtime"))
    monkeypatch.setattr(service, "PID_FILE", Path("data/runtime/tl_gui.pid"))
    monkeypatch.setattr(service, "LOG_FILE", Path("data/runtime/tl_gui.log"))
    monkeypatch.setattr(service, "_server_responds", lambda host, port: False)

    state = service.status()
    assert state.running is False
    assert state.pid is None
    assert str(state.url).endswith(":811/")


def test_service_stop_removes_pid_file_without_real_process(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runtime = Path("data/runtime")
    runtime.mkdir(parents=True)
    pid_file = runtime / "tl_gui.pid"
    pid_file.write_text("999999", encoding="utf-8")

    monkeypatch.setattr(service, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(service, "PID_FILE", pid_file)
    monkeypatch.setattr(service, "LOG_FILE", runtime / "tl_gui.log")
    monkeypatch.setattr(service, "_pid_is_running", lambda pid: False)
    monkeypatch.setattr(service, "_server_responds", lambda host, port: False)

    state = service.stop()
    assert state.running is False
    assert not pid_file.exists()


def test_cli_has_top_level_service_shortcuts():
    import trading_lab.cli.main as cli_main

    text = Path(cli_main.__file__).read_text(encoding="utf-8")
    assert '"start", "stop", "service"' in text
