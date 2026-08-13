from datetime import UTC, datetime, timedelta

from endpoint.analysis import build_graph
from endpoint.models import Certainty, Transfer


def transfer(identifier, source, target, amount, offset, asset="SOL"):
    return Transfer(
        id=identifier,
        signature=f"sig-{identifier}",
        slot=100 + offset,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset),
        source=source,
        target=target,
        asset=asset,
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


def test_endpoint_ranking_ignores_dust_and_finds_terminal_value_flow():
    seed = "seed"
    endpoint = "real-endpoint"
    dust_targets = [f"dust-target-{index}" for index in range(8)]
    transfers = [
        transfer("usdc-1", seed, endpoint, "10", 1, "USDC"),
        transfer("usdc-2", seed, endpoint, "25", 2, "USDC"),
        transfer("usdc-3", seed, endpoint, "50", 3, "USDC"),
        transfer("usdc-4", seed, endpoint, "50.43105", 4, "USDC"),
        transfer("sol-endpoint", seed, endpoint, "0.2966", 5),
        transfer("sol-other", seed, "small-terminal", "0.013125", 6),
    ]
    for index, target in enumerate(dust_targets):
        transfers.extend(
            [
                transfer(f"dust-a-{index}", "dust-source-a", target, "0.000000001", 20 + index),
                transfer(f"dust-b-{index}", "dust-source-b", target, "0.000000001", 40 + index),
            ]
        )

    _, edges, _, candidates = build_graph(seed, transfers)

    assert candidates[0].address == endpoint
    assert candidates[0].terminal_in_observed_graph is True
    assert candidates[0].direct_from_seed is True
    assert candidates[0].incoming_transfer_count == 5
    assert {total.asset: total.amount for total in candidates[0].received_assets} == {
        "SOL": "0.2966",
        "USDC": "135.43105",
    }
    candidate_addresses = {candidate.address for candidate in candidates}
    assert all(target not in candidate_addresses for target in dust_targets)
    assert sum(edge.transfer_count for edge in edges if edge.probable_noise) == 16
    assert not any(
        edge.certainty == Certainty.HEURISTIC
        and edge.source in dust_targets
        and edge.target in dust_targets
        for edge in edges
    )
