"""Counts-only simultaneous quota proof. No ranking, selection or witness reconstruction."""

import itertools
from collections import Counter
from experiments.reviewer_protocol_v2.common import require
from experiments.reviewer_protocol_v2.eligibility import STRATA, QUOTAS
from experiments.reviewer_protocol_v2.similarity import cos, conflicts, grams


def constraint_summary(rows, quotas=None):
    quotas = QUOTAS if quotas is None else quotas
    require(
        set(quotas) == set(STRATA)
        and all(type(q) is int and q >= 0 for q in quotas.values()),
        "invalid_quotas",
    )
    capacity = Counter((r["source"], r["sampling_stratum"]) for r in rows)
    adjacency = {i: set() for i in range(len(rows))}
    native_count = similarity_count = both_count = 0
    native_strata, similarity_strata = Counter(), Counter()
    vectors = [grams(row["question"]) for row in rows]
    for i, j in itertools.combinations(range(len(rows)), 2):
        left, right = rows[i], rows[j]
        native = (left["source"], left["context_group"]) == (
            right["source"],
            right["context_group"],
        )
        similar = conflicts(cos(vectors[i], vectors[j]))
        key = "|".join(
            sorted(
                (
                    left["source"] + "/" + left["sampling_stratum"],
                    right["source"] + "/" + right["sampling_stratum"],
                )
            )
        )
        native_count += native
        similarity_count += similar
        both_count += native and similar
        if native:
            native_strata[key] += 1
        if similar:
            similarity_strata[key] += 1
        if native or similar:
            adjacency[i].add(j)
            adjacency[j].add(i)
    isolated = Counter(
        (rows[i]["source"], rows[i]["sampling_stratum"])
        for i, neighbours in adjacency.items()
        if not neighbours
    )
    remaining = {i for i, neighbours in adjacency.items() if neighbours}
    components = []
    while remaining:
        frontier = [min(remaining)]
        component = set()
        while frontier:
            i = frontier.pop()
            if i in component:
                continue
            component.add(i)
            frontier.extend(adjacency[i] - component)
        remaining -= component
        components.append(sorted(component))
    # Compute only count vectors for independent sets within conflict components.
    # The bounded solver refuses graphs beyond its reviewed offline resource envelope.
    possible = {tuple(0 for _ in STRATA)}
    limits = tuple(quotas[s] for s in STRATA)
    component_sizes = []
    for component in components:
        require(
            len(component) <= 20, "constraint_component_exceeds_offline_solver_bound"
        )
        component_sizes.append(len(component))
        local = set()
        for bits in range(1 << len(component)):
            indices = {component[k] for k in range(len(component)) if bits & (1 << k)}
            if any(adjacency[i] & indices for i in indices):
                continue
            count = Counter(
                (rows[i]["source"], rows[i]["sampling_stratum"]) for i in indices
            )
            local.add(tuple(min(count[s], quotas[s]) for s in STRATA))
        possible = {
            tuple(min(a + b, limit) for a, b, limit in zip(x, y, limits))
            for x in possible
            for y in local
        }
    feasible = any(
        all(n + isolated[s] >= quotas[s] for s, n in zip(STRATA, vector))
        for vector in possible
    )
    return {
        "retained_pair_comparisons": len(rows) * (len(rows) - 1) // 2,
        "native_group_conflicts": native_count,
        "similarity_conflicts": similarity_count,
        "native_similarity_overlap": both_count,
        "native_conflicts_by_strata": dict(sorted(native_strata.items())),
        "similarity_conflicts_by_strata": dict(sorted(similarity_strata.items())),
        "strata": [
            {
                "source": s,
                "stratum": t,
                "capacity": capacity[(s, t)],
                "quota": quotas[(s, t)],
                "conflict_free_capacity": isolated[(s, t)],
                "distinct_native_groups": len(
                    {
                        row["context_group"]
                        for row in rows
                        if (row["source"], row["sampling_stratum"]) == (s, t)
                    }
                ),
            }
            for s, t in STRATA
        ],
        "conflict_component_sizes": component_sizes,
        "simultaneous_quota_feasible": feasible,
        "proof": "independent-set count vectors plus conflict-free capacities; no witness retained",
    }


def validate_diversity(rows):
    result = constraint_summary(rows, {s: 0 for s in STRATA})
    require(result["native_group_conflicts"] == 0, "packet_native_group_conflict")
    require(result["similarity_conflicts"] == 0, "packet_direct_similarity_conflict")
    return True
