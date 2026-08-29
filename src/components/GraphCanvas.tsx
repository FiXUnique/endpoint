import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useRef } from "react";

import type { Investigation, Selection } from "../types";

interface GraphCanvasProps {
  investigation: Investigation;
  onSelect: (selection: Selection) => void;
}

function shortened(address: string): string {
  return `${address.slice(0, 5)}…${address.slice(-4)}`;
}

export function GraphCanvas({ investigation, onSelect }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const visibleEdges = investigation.edges.filter(
      (edge) => edge.certainty === "confirmed_fact" && !edge.probable_noise,
    );
    const visibleNodeIds = new Set([
      investigation.seed,
      ...visibleEdges.flatMap((edge) => [edge.source, edge.target]),
    ]);
    const visibleNodes = investigation.nodes.filter((node) => visibleNodeIds.has(node.id));
    const nodeMap = new Map(visibleNodes.map((node) => [node.id, node]));
    const edgeMap = new Map(visibleEdges.map((edge) => [edge.id, edge]));
    const candidateAddresses = new Set(
      investigation.exit_candidates
        .filter((item) => item.terminal_in_observed_graph)
        .map((item) => item.address),
    );
    const elements: ElementDefinition[] = [
      ...visibleNodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label ?? shortened(node.address),
          nodeType: node.seed ? "seed" : candidateAddresses.has(node.address) ? "candidate" : "wallet",
        },
      })),
      ...visibleEdges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          certainty: edge.certainty,
          relationship: edge.relationship,
        },
      })),
    ];

    const graph = cytoscape({
      container: containerRef.current,
      elements,
      minZoom: 0.2,
      maxZoom: 2.5,
      style: [
        {
          selector: "node",
          style: {
            width: 42,
            height: 42,
            label: "data(label)",
            color: "#aeb8cb",
            "font-size": 9,
            "font-family": "Inter, ui-sans-serif, system-ui",
            "text-valign": "bottom",
            "text-margin-y": 8,
            "background-color": "#151b28",
            "border-width": 1.5,
            "border-color": "#667085",
            "overlay-opacity": 0,
          },
        },
        {
          selector: 'node[nodeType = "seed"]',
          style: {
            width: 54,
            height: 54,
            "background-color": "#192d2a",
            "border-width": 2.5,
            "border-color": "#52e2b2",
            color: "#d8fff1",
          },
        },
        {
          selector: 'node[nodeType = "candidate"]',
          style: {
            "background-color": "#312719",
            "border-color": "#f5b95c",
            color: "#ffe5b9",
            shape: "diamond",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.6,
            "line-color": "#526174",
            "target-arrow-color": "#526174",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "",
            color: "#8390a5",
            "font-size": 8,
            "text-background-color": "#080b12",
            "text-background-opacity": 0.85,
            "text-background-padding": "3px",
          },
        },
        {
          selector: 'edge[certainty = "heuristic_relationship"]',
          style: {
            "line-style": "dashed",
            "line-color": "#846cbb",
            "target-arrow-shape": "none",
            color: "#a794d7",
          },
        },
        {
          selector: ":selected",
          style: {
            "border-color": "#ffffff",
            "border-width": 3,
            "line-color": "#ffffff",
            "target-arrow-color": "#ffffff",
          },
        },
        {
          selector: "edge:selected",
          style: {
            label: "data(label)",
            "font-size": 9,
          },
        },
      ],
      layout: {
        name: "cose",
        animate: false,
        idealEdgeLength: 120,
        nodeRepulsion: 9000,
        randomize: true,
        fit: true,
        padding: 60,
      },
    });
    graph.on("tap", "node", (event) => {
      const node = nodeMap.get(event.target.id());
      if (node) onSelect({ kind: "node", value: node });
    });
    graph.on("tap", "edge", (event) => {
      const edge = edgeMap.get(event.target.id());
      if (edge) onSelect({ kind: "edge", value: edge });
    });
    graph.on("tap", (event) => {
      if (event.target === graph) onSelect(null);
    });
    graphRef.current = graph;
    return () => {
      graph.destroy();
      graphRef.current = null;
    };
  }, [investigation, onSelect]);

  return (
    <div className="graph-wrap">
      <div className="graph-legend" aria-label="Graph legend">
        <span><i className="legend-dot seed" /> Starting wallet</span>
        <span><i className="legend-dot wallet" /> Other wallet</span>
        <span><i className="legend-dot candidate" /> Trail stops here</span>
      </div>
      <div className="graph-canvas" ref={containerRef} aria-label="Interactive fund-flow graph" />
      <div className="graph-help">Drag to move · Scroll to zoom · Click a wallet for details</div>
    </div>
  );
}
