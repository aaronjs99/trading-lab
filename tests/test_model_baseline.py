from pathlib import Path

from trading_lab.models.baseline import write_manual_baseline


def test_write_manual_baseline(tmp_path: Path):
    out = tmp_path / "baseline.csv"

    df = write_manual_baseline(
        model="rf",
        mean_roc_auc=0.60,
        mean_profit_factor=2.30,
        mean_win_rate=0.67,
        worst_fold_drawdown=-0.42,
        output_path=out,
    )

    assert out.exists()
    assert df.iloc[0]["model"] == "rf"
    assert df.iloc[0]["mean_profit_factor"] == 2.30
