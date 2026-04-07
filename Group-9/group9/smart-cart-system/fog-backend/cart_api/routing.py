"""
routing.py — Indoor pathfinding service for the Smart Cart System.

Builds a walkable graph from RoutePath records drawn by the retailer,
snaps arbitrary (x, y) coordinates to the nearest graph node, and
computes the shortest path using Dijkstra's algorithm via networkx.
"""

import math

import networkx as nx
from scipy.spatial.distance import cdist

from .models import RoutePath


SNAP_TOLERANCE = 0.03  # 3 % of the map — matches typical hand-drawn jitter


def _snap(coord, canonical, tol=SNAP_TOLERANCE):
    """Return the first canonical node within *tol* of *coord*, else *coord* itself."""
    for c in canonical:
        if math.dist(coord, c) <= tol:
            return c
    return coord


def build_graph():
    """
    Query all RoutePath segments and return an undirected networkx.Graph.

    Nodes are (x, y) tuples (float percentages 0.0–1.0).
    Edges carry a ``weight`` equal to the segment's Euclidean length.

    Nearby endpoints (within ``SNAP_TOLERANCE``) are merged so that
    hand-drawn segments with slight coordinate jitter still form a
    connected walkable graph.
    """
    G = nx.Graph()
    canonical_nodes: list[tuple[float, float]] = []

    for rp in RoutePath.objects.all():
        raw_start = (rp.start_x, rp.start_y)
        raw_end = (rp.end_x, rp.end_y)

        start = _snap(raw_start, canonical_nodes)
        if start == raw_start:          # new unique node
            canonical_nodes.append(start)

        end = _snap(raw_end, canonical_nodes)
        if end == raw_end:              # new unique node
            canonical_nodes.append(end)

        weight = math.dist(start, end) if start != end else 0.0001
        G.add_edge(start, end, weight=weight)

    # Auto-bridge disconnected components so pathfinding always succeeds
    _bridge_components(G)

    return G


def _bridge_components(G):
    """Connect disconnected graph components by adding edges between nearest node pairs.

    For each pair of disconnected components, find the two nodes (one from each)
    that are geographically closest and add an edge between them. Repeat until the
    entire graph is connected. The bridging edges use a slight weight penalty (1.5×)
    to prefer the retailer-drawn paths when available.
    """
    while True:
        components = list(nx.connected_components(G))
        if len(components) <= 1:
            break

        # Find the two closest components (by nearest node pair)
        best_dist = float("inf")
        best_pair = None
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                nodes_a = list(components[i])
                nodes_b = list(components[j])
                distances = cdist(
                    [[n[0], n[1]] for n in nodes_a],
                    [[n[0], n[1]] for n in nodes_b],
                    metric="euclidean",
                )
                min_idx = distances.argmin()
                row, col = divmod(min_idx, len(nodes_b))
                d = distances[row][col]
                if d < best_dist:
                    best_dist = d
                    best_pair = (nodes_a[row], nodes_b[col])

        if best_pair is None:
            break

        # Add a bridging edge with a slight penalty so drawn paths are preferred
        G.add_edge(best_pair[0], best_pair[1], weight=best_dist * 1.5)


def find_nearest_node(graph, x, y):
    """
    Return the graph node closest to the given (x, y) coordinate.

    Uses scipy's ``cdist`` for efficient distance computation.
    Returns ``None`` if the graph has no nodes.
    """
    nodes = list(graph.nodes)
    if not nodes:
        return None

    # cdist expects 2-D arrays: [[x, y]] vs [[nx, ny], ...]
    point = [[x, y]]
    node_coords = [[n[0], n[1]] for n in nodes]
    distances = cdist(point, node_coords, metric="euclidean")[0]

    nearest_idx = distances.argmin()
    return nodes[nearest_idx]


def compute_route(start_x, start_y, dest_x, dest_y):
    """
    Compute the shortest walkable path between two arbitrary coordinates.

    Parameters
    ----------
    start_x, start_y : float
        Cart's current position (percentage coordinates).
    dest_x, dest_y : float
        Destination zone centre (percentage coordinates).

    Returns
    -------
    list[dict]
        Ordered list of ``{"x": float, "y": float}`` waypoints.
        Includes the original start and destination as the first and
        last points, with graph nodes in between.

    Edge-case handling
    ------------------
    * **No RoutePaths drawn** → returns a straight line ``[start, dest]``.
    * **No path exists** between the two snapped nodes (disconnected
      graph) → falls back to a straight line.
    """
    start_point = {"x": start_x, "y": start_y}
    dest_point = {"x": dest_x, "y": dest_y}

    G = build_graph()

    # ── Fallback: no graph at all ──────────────────────────────────────
    if G.number_of_nodes() == 0:
        return [start_point, dest_point]

    # ── Snap to nearest nodes ──────────────────────────────────────────
    source = find_nearest_node(G, start_x, start_y)
    target = find_nearest_node(G, dest_x, dest_y)

    if source is None or target is None:
        return [start_point, dest_point]

    # Same node — just go straight through it
    if source == target:
        return [
            start_point,
            {"x": source[0], "y": source[1]},
            dest_point,
        ]

    # ── Shortest path via Dijkstra ─────────────────────────────────────
    try:
        path_nodes = nx.shortest_path(G, source=source, target=target, weight="weight")
    except nx.NetworkXNoPath:
        return [start_point, dest_point]

    # ── Construct final waypoint list ──────────────────────────────────
    waypoints = [start_point]
    for node in path_nodes:
        waypoints.append({"x": node[0], "y": node[1]})
    waypoints.append(dest_point)

    return waypoints
