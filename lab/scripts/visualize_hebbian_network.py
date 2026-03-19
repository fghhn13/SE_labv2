from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - optional dependency
    tqdm = None


def load_hebbian_state(neurons_file: Path) -> Dict:
    if not neurons_file.exists():
        raise FileNotFoundError(f"neurons file not found: {neurons_file}")
    data = json.loads(neurons_file.read_text(encoding="utf-8"))
    runtime = data.get("runtime", {})
    return {
        "neurons": runtime.get("neurons", []),
        "synapses": runtime.get("synapses", []),
    }


def build_graph(
    neurons: List[Dict],
    synapses: List[Dict],
    min_weight: float,
    use_abs_threshold: bool = True,
    top_k: int = 0,
) -> nx.DiGraph:
    """
    Build directed graph from neurons and synapses.
    Nodes use neuron "id". Edges are thresholded by min_weight.
    If top_k > 0, only keep the top K absolute weight outgoing edges for each node.
    """
    G = nx.DiGraph()

    # Node set
    node_ids: set[int] = set()
    for idx, n in enumerate(neurons):
        nid = n.get("id")
        node_ids.add(int(nid) if nid is not None else idx)
        
    for nid in node_ids:
        G.add_node(nid)

    total_synapses = len(synapses)
    if total_synapses == 0:
        print("[hebbian-vis] no synapses in file.", file=sys.stderr)
        return G

    print(f"[hebbian-vis] building graph: {total_synapses} synapses (min |weight|={min_weight})")
    
    # Pre-filter by threshold
    filtered_edges = []
    iterator = synapses
    if tqdm is not None:
        iterator = tqdm(synapses, total=total_synapses, desc="[hebbian-vis] synapses", unit="edge")
    for edge in iterator:
        i = int(edge.get("from", 0))
        j = int(edge.get("to", 0))
        w = float(edge.get("weight", 0.0))
        
        if use_abs_threshold:
            if abs(w) <= min_weight: continue
        else:
            if w <= min_weight: continue
            
        filtered_edges.append((i, j, w))

    # Apply Top-K filtering if requested
    if top_k > 0:
        print(f"[hebbian-vis] applying Top-{top_k} outgoing edges filter...")
        # Group by source node
        out_edges = {nid: [] for nid in node_ids}
        for i, j, w in filtered_edges:
            if i in out_edges:
                out_edges[i].append((j, w))
        
        filtered_edges = []
        for i, edges in out_edges.items():
            # Sort by absolute weight descending and take top_k
            edges.sort(key=lambda x: abs(x[1]), reverse=True)
            for j, w in edges[:top_k]:
                filtered_edges.append((i, j, w))

    # Add edges to graph
    for i, j, w in filtered_edges:
        if i not in node_ids: G.add_node(i); node_ids.add(i)
        if j not in node_ids: G.add_node(j); node_ids.add(j)
        G.add_edge(i, j, weight=w)

    print(f"[hebbian-vis] kept {G.number_of_edges()} synapses after thresholding and Top-K filter.")
    return G


def detect_communities(G: nx.DiGraph) -> Dict[int, int]:
    """
    Detect communities using Louvain.
    Fix: Louvain fails with negative weights, so we build a strictly positive undirected graph for community detection.
    """
    try:
        import community as community_louvain  # type: ignore[import]
    except Exception:
        try:
            import community_louvain  # type: ignore[import]
        except Exception:
            return {n: 0 for n in G.nodes()}

    if G.number_of_nodes() == 0:
        return {}

    # Build an undirected graph using ONLY positive weights for Louvain
    undirected = nx.Graph()
    for u, v, data in G.edges(data=True):
        w = data.get("weight", 0.0)
        if w > 0:
            if undirected.has_edge(u, v):
                undirected[u][v]['weight'] += w
            else:
                undirected.add_edge(u, v, weight=w)
                
    for n in G.nodes():
        undirected.add_node(n)

    partition = community_louvain.best_partition(undirected)
    return partition


def _compute_layout(G: nx.DiGraph, layout: str, seed: int = 0) -> Dict[int, Tuple[float, float]]:
    if layout == "spring":
        return nx.spring_layout(G, seed=seed, k=0.5, iterations=100) # Slightly looser spread
    if layout == "shell":
        return nx.shell_layout(G)
    if layout == "kamada_kawai":
        # Kamada-Kawai relies on shortest paths; negative weights can break Dijkstra.
        # Use unweighted path lengths for stable layout with signed edges.
        return nx.kamada_kawai_layout(G, weight=None)
    return nx.spring_layout(G, seed=seed)


def draw_graph(
    G: nx.DiGraph,
    partition: Dict[int, int],
    output_file: Path,
    title: str,
    layout: str = "spring",
    largest_cc_only: bool = False,
) -> None:
    if G.number_of_nodes() == 0:
        print("Graph is empty; nothing to draw.")
        return

    if largest_cc_only and G.number_of_nodes() > 1:
        undirected = G.to_undirected()
        largest = max(nx.connected_components(undirected), key=len)
        G = G.subgraph(largest).copy()
        print(f"[hebbian-vis] drawing largest cc: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    pos = _compute_layout(G, layout)

    communities = sorted(set(partition.values()))
    color_map = plt.cm.get_cmap("tab20", max(2, len(communities)))

    node_colors = []
    for n in G.nodes():
        cid = partition.get(n, 0)
        idx = communities.index(cid) if cid in communities else 0
        node_colors.append(color_map(idx))

    node_sizes = [min(800, max(150, 200 + 30 * G.degree(n))) for n in G.nodes()]

    def edge_width(w: float) -> float:
        return max(0.5, min(2.0, 0.5 * math.sqrt(abs(w)))) # slightly thicker

    edges_positive = []
    edges_negative = []
    widths_pos = []
    widths_neg = []
    
    for u, v in G.edges():
        w = G[u][v].get("weight", 0.0)
        if w >= 0:
            edges_positive.append((u, v))
            widths_pos.append(edge_width(w))
        else:
            edges_negative.append((u, v))
            widths_neg.append(edge_width(w))

    plt.figure(figsize=(16, 12))
    nx.draw_networkx_labels(
        G, pos, 
        font_size=10, 
        font_color="black", 
        font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=0.3)
    )

    # Add connectionstyle="arc3,rad=0.15" to curve the edges and prevent overlapping lines
    if edges_positive:
        nx.draw_networkx_edges(
            G, pos, edgelist=edges_positive, width=widths_pos,
            edge_color="tab:gray", alpha=0.6, arrows=True,
            arrowstyle="-|>", arrowsize=10, style="solid",
            connectionstyle="arc3,rad=0.15"
        )
    if edges_negative:
        nx.draw_networkx_edges(
            G, pos, edgelist=edges_negative, width=widths_neg,
            edge_color="tab:red", alpha=0.5, arrows=True,
            arrowstyle="-|>", arrowsize=10, style="dashed",
            connectionstyle="arc3,rad=0.15"
        )

    nx.draw_networkx_labels(G, pos, font_size=8, font_color="black", font_weight="bold")

    plt.title(title, fontsize=14, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"[hebbian-vis] wrote graph to {output_file}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Visualize Hebbian synapse network.")
    parser.add_argument("--neurons-file", type=str, required=True, help="Path to neurons.json.")
    parser.add_argument("--output-file", type=str, default=None, help="Output image path.")
    parser.add_argument("--min-weight", type=float, default=1.0, help="Filter out |weight| <= min_weight.")
    parser.add_argument("--top-k", type=int, default=0, help="Keep only Top-K absolute weight outgoing edges per node.")
    parser.add_argument("--positive-only", action="store_true", help="Only draw positive edges.")
    parser.add_argument("--use-communities", action="store_true", help="Try Louvain community coloring.")
    parser.add_argument("--layout", type=str, default="spring", choices=("spring", "shell", "kamada_kawai"))
    parser.add_argument("--largest-cc", action="store_true", help="Draw only largest connected component.")
    args = parser.parse_args(argv)

    neurons_path = Path(args.neurons_file)
    state = load_hebbian_state(neurons_path)
    
    G = build_graph(
        state["neurons"], state["synapses"],
        min_weight=args.min_weight,
        use_abs_threshold=not args.positive_only,
        top_k=args.top_k,
    )

    out = Path(args.output_file) if args.output_file else neurons_path.with_name("hebbian_network.png")
    partition = detect_communities(G) if args.use_communities else {n: 0 for n in G.nodes()}

    title = f"Hebbian Core Network (|V|={G.number_of_nodes()}, |E|={G.number_of_edges()})"
    draw_graph(G, partition, out, title=title, layout=args.layout, largest_cc_only=args.largest_cc)


if __name__ == "__main__":
    main()