from pathlib import Path

from src.blackfen.evals import run_eval_suite
from src.blackfen.report import write_report_packet
from src.blackfen.rng import SeededRng
from src.blackfen.scenario import load_action_script, run_action_script
from src.blackfen.snapshot import load_checkpoint, save_checkpoint
from src.blackfen.trace import build_trace_package, load_trace, replay_trace, save_trace


def test_checkpoint_round_trips_state_and_rng(tmp_path: Path) -> None:
    script = load_action_script(Path("tests/blackfen/fixtures/victory-path.yaml"))
    result = run_action_script(script)
    rng = SeededRng.from_snapshot(result.state.seed, SeededRng(result.state.seed).snapshot())

    path = save_checkpoint(result.state, rng, "victory", root=tmp_path)
    loaded_state, loaded_rng, package = load_checkpoint(path)

    assert package.name == "victory"
    assert loaded_state == result.state
    assert loaded_rng.snapshot() == rng.snapshot()


def test_trace_replay_uses_recorded_turn_contract(tmp_path: Path) -> None:
    script = load_action_script(Path("tests/blackfen/fixtures/victory-path.yaml"))
    result = run_action_script(script)
    trace_path = save_trace(build_trace_package(result), tmp_path / "trace.json")

    package = load_trace(trace_path)
    replayed = replay_trace(package)

    assert replayed.final_hash == result.final_hash
    assert replayed.turns[-1].narration == result.turns[-1].narration


def test_report_packet_writes_html_and_raw_trace(tmp_path: Path) -> None:
    script = load_action_script(Path("tests/blackfen/fixtures/victory-path.yaml"))
    trace_path = save_trace(build_trace_package(run_action_script(script)), tmp_path / "trace.json")

    report_path = write_report_packet(trace_path, tmp_path / "packet")

    assert report_path.is_file()
    assert (tmp_path / "packet" / "raw-trace.json").is_file()
    assert "Blackfen Road Review Packet" in report_path.read_text(encoding="utf-8")


def test_blackfen_eval_suite_writes_results_and_trace(tmp_path: Path) -> None:
    results = run_eval_suite(out_dir=tmp_path)

    assert [result.passed for result in results] == [True]
    assert (tmp_path / "results.json").is_file()
    assert (tmp_path / "traces" / "blackfen-victory-path.json").is_file()
