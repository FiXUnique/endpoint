from datetime import UTC, datetime, timedelta

from endpoint.analysis import build_graph
from endpoint.models import Certainty, Transfer


def transfer(identifier, source, target, amount, offset):
    return Transfer(
        id=identifier,
        signature=f"sig-{identifier}",
        slot=100 + offset,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset),
        source=source,
        target=target,
        asset="SOL",
        amount=amount,
        decimals=9,
        kind="native_transfer",
        instruction_path=f"outer:{offset}",
    )


def test_builds_fact_edges_and_reproducible_heuristics():
    transfers = [
        transfer("one", "funder", "wallet-a", "10", 0),
        transfer("two", "funder", "wallet-b", "11", 30),
        transfer("three", "wallet-a", "sink", "9", 200),
        transfer("four", "wallet-b", "sink", "10", 210),
    ]

    nodes, edges, evidence, candidates = build_graph("funder", transfers)

    assert len(nodes) == 4
    assert len(evidence) == 4
    facts = [edge for edge in edges if edge.certainty == Certainty.CONFIRMED]
    heuristics = [edge for edge in edges if edge.certainty == Certainty.HEURISTIC]
    assert len(facts) == 4
    assert len(heuristics) == 1
    assert heuristics[0].evidence_score == 0.6
    assert {signal.type for signal in heuristics[0].signals} == {
        "common_funder",
        "temporal_proximity",
    }
    assert candidates[0].address == "sink"
    assert "not an attribution" in candidates[0].explanation


def test_transfer_edge_aggregates_matching_flows_without_losing_evidence():
    transfers = [
        transfer("one", "a", "b", "1.5", 0),
        transfer("two", "a", "b", "2.25", 5),
    ]
    _, edges, evidence, _ = build_graph("a", transfers)

    assert len(edges) == 1
    assert edges[0].amount == "3.75"
    assert edges[0].transfer_count == 2
    assert edges[0].evidence_ids == ["one", "two"]
    assert len(evidence) == 2
