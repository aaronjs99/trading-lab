from trading_lab.devtools import audit


def test_audit_reports_tracked_private_and_generated_files(monkeypatch, capsys):
    monkeypatch.setattr(
        audit,
        "tracked_files",
        lambda: {
            "data/private.csv",
            "reports/generated.md",
            "src/trading_lab/__pycache__/x.pyc",
            "src/trading_lab/config/settings.py",
        },
    )
    monkeypatch.setattr(audit, "clean_local_cruft", lambda: 0)

    audit.main()

    output = capsys.readouterr().out
    assert "BAD_TRACKED data/private.csv" in output
    assert "BAD_TRACKED reports/generated.md" in output
    assert "BAD_TRACKED src/trading_lab/__pycache__/x.pyc" in output
    assert "src/trading_lab/config/settings.py" not in output
