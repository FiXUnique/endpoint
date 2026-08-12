from endpoint.analysis import build_graph
from endpoint.demo import synthetic_demo_transfers
from endpoint.models import InvestigationGraph, TraceLimits
from endpoint.repository import InvestigationRepository


def test_snapshot_round_trip(tmp_path):
    seed, transfers = synthetic_demo_transfers()
    nodes, edges, evidence, candidates = build_graph(seed, transfers)
    graph = InvestigationGraph(
        investigation_id="inv-test",
        name="Test",
        seed=seed,
        data_source="synthetic_demo",
        nodes=nodes,
        edges=edges,
        evidence=evidence,
        exit_candidates=candidates,
        limits=TraceLimits(requested_signatures=0, returned_signatures=0, truncated=False),
    )
    repository = InvestigationRepository(str(tmp_path / "endpoint.db"))

    repository.save(graph)

    loaded = repository.get("inv-test")
    assert loaded is not None
    assert loaded.model_dump() == graph.model_dump()
    assert repository.list()[0]["name"] == "Test"
