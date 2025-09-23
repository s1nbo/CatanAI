// HexGrid React component (Plain React + Tailwind + CSS)
// Tiles: 0–18, Vertices: 0–53, Edges: 0–71
// Each object now includes attributes, and here we assign some test values for resources, numbers, and owners.

import React, { useMemo, useState } from "react";

// --- Type Definitions ---
interface Vertex {
  id: number;
  x: number; y: number;
  building: string | null;
  owner: number | null;
  port: string | null;
  blocked: boolean;
}
interface Edge {
  id: number;
  v1: number; v2: number;
  x1: number; y1: number; x2: number; y2: number;
  mx: number; my: number;
  owner: number | null;
}
interface Tile {
  id: number;
  cx: number; cy: number;
  pts: { x: number; y: number; }[];
  keys: string[];
  vertexIds: number[];
  edgeIds: number[];
  resource: keyof typeof RESOURCE_COLORS;
  number: number;
  robber: boolean | null;
}
interface Geometry { tiles: Tile[]; vertices: Record<number, Vertex>; edges: Record<number, Edge>; }
type LastClick = { type: 'tile' | 'edge' | 'vertex'; id: number } | null;

const HEX_SIZE = 64;
const VERTEX_ROW_COUNTS = [7, 9, 11, 11, 9, 7];
const SNAP_K = 1000;
const EDGE_STROKE = 6;

// Darker, dimmed tile colors for better eye comfort
const RESOURCE_COLORS = {
  Wood: "#14532d",   // darker green
  Brick: "#9a3412",  // dark orange-brown
  Sheep: "#65a30d",  // lighter green for sheep
  Wheat: "#ca8a04",  // dark golden yellow
  Ore: "#4b5563",    // dark gray
  Desert: "#e7e5e4", // muted beige
  null: "#e5e7eb",   // neutral gray
};

// Player colors: orange, purple, dark blue, light blue
const PLAYER_COLORS = {
  1: "#f97316", // orange
  2: "#a855f7", // purple
  3: "#1448d5ff", // dark blue
  4: "#000000ff", // light blue
  null: "#374151",
};

function hexToPixel(q: number, r: number, size: number): { x: number; y: number } {
  const x = size * Math.sqrt(3) * (q + r / 2);
  const y = size * (3 / 2) * r;
  return { x, y };
}

function snap(v: number): number {
  return Math.round(v * SNAP_K) / SNAP_K;
}

function vKey(x: number, y: number): string {
  return `${snap(x)}_${snap(y)}`;
}

function generateHexes(radius: number): { q: number; r: number }[] {
  const hexes: { q: number; r: number }[] = [];
  for (let q = -radius; q <= radius; q++) {
    const r1 = Math.max(-radius, -q - radius);
    const r2 = Math.min(radius, -q + radius);
    for (let r = r1; r <= r2; r++) {
      hexes.push({ q, r });
    }
  }
  return hexes;
}

export default function HexBoard({ radius = 2, size = HEX_SIZE }) {
  const hexes = useMemo(() => generateHexes(radius), [radius]);

  const hexesWithIds = useMemo(() => {
    const withCoords = hexes.map((h) => {
      const { x, y } = hexToPixel(h.q, h.r, size);
      return { ...h, cx: x, cy: y };
    });
    withCoords.sort((a, b) => (a.cy === b.cy ? a.cx - b.cx : a.cy - b.cy));
    return withCoords.map((h, idx) => ({ ...h, id: idx }));
  }, [hexes, size]);

  const geometry: Geometry = useMemo(() => {
    const tilesDraft: { cx: number; cy: number; pts: { x: number; y: number }[]; keys: string[] }[] = [];
    const vertexIndex: Record<string, { x: number; y: number }> = {};

    for (const { q, r, cx, cy } of hexesWithIds) {
      const pts = [];
      const keys = [];
      for (let i = 0; i < 6; i++) {
        const angle = ((60 * i - 30) * Math.PI) / 180;
        const x = cx + size * Math.cos(angle);
        const y = cy + size * Math.sin(angle);
        const k = vKey(x, y);
        const sx = snap(x);
        const sy = snap(y);
        pts.push({ x: sx, y: sy });
        keys.push(k);
        if (!vertexIndex[k]) vertexIndex[k] = { x: sx, y: sy };
      }
      tilesDraft.push({ cx, cy, pts, keys });
    }

    const vEntries: [string, { x: number; y: number }][] = Object.entries(vertexIndex);
    vEntries.sort(([, a], [, b]) => (a.y === b.y ? a.x - b.x : a.y - b.y));

    const rows: [string, { x: number; y: number }][][] = [];
    let current: [string, { x: number; y: number }][] = [];
    let lastY: number | null = null;
    const yThreshold = size * 0.35;
    for (const [k, v] of vEntries) {
      if (lastY === null || Math.abs(v.y - lastY) <= yThreshold) {
        current.push([k, v]);
        lastY = lastY === null ? v.y : (lastY * (current.length - 1) + v.y) / current.length;
      } else {
        rows.push(current);
        current = [[k, v]];
        lastY = v.y;
      }
    }
    if (current.length) rows.push(current);

    if (rows.length !== VERTEX_ROW_COUNTS.length) {
      const sliced = [];
      let cursor = 0;
      for (const count of VERTEX_ROW_COUNTS) {
        sliced.push(vEntries.slice(cursor, cursor + count));
        cursor += count;
      }
      rows.length = 0;
      rows.push(...sliced);
    }

    // Build vertices with IDs 0..53 in zig-zag rows
    const vertices = {};
    const keyToVid = {};
    const portTypes = ["3:1", "2:1 Wood", "2:1 Brick", "2:1 Sheep", "2:1 Wheat", "2:1 Ore"];
    let vid = 0;
    for (let r = 0; r < rows.length; r++) {
      const row = rows[r].slice().sort(([, a], [, b]) => a.x - b.x);
      for (const [k, v] of row) {
        // Assign ports only to outer edge vertices
        let portType = null;
        const isOuterVertex = (r === 0 || r === rows.length - 1) ||
          (v.x < -100 || v.x > 100 || v.y < -100 || v.y > 100);

        // Force wheat port on a specific vertex for testing (regardless of outer status)
        if (vid === 5) {
          portType = "2:1 Wheat"; // Test wheat port
        } else if (isOuterVertex) {
          if (vid % 9 === 2 || vid % 13 === 5 || vid % 17 === 3) {
            portType = "3:1"; // More 3:1 ports
          } else if (vid % 11 === 7) {
            portType = portTypes[1 + (vid % 5)]; // Specialty ports
          }
        }

        vertices[vid] = {
          id: vid,
          x: v.x,
          y: v.y,
          building: vid % 11 === 0 ? "City" : null,
          owner: vid % 5 === 0 ? (vid % 4) + 1 : null,
          port: portType,
          blocked: false,
        };
        keyToVid[k] = vid;
        vid++;
      }
    }

    // Prepare tiles (assign fake resources/numbers/robber for demo)
    const sampleResources = ["Wood", "Brick", "Sheep", "Wheat", "Ore", "Desert"];
    const tiles: Tile[] = tilesDraft.map((t, idx) => ({
      ...t,
      id: idx,
      vertexIds: t.keys.map((k) => keyToVid[k]),
      resource: sampleResources[idx % sampleResources.length],
      number: (idx % 11) + 2,
      robber: idx === 0 ? true : null,
    }));

    // Build unique edges from vertex pairs
    const edgeMap = new Map<string, { v1: number; v2: number; x1: number; y1: number; x2: number; y2: number }>();
    for (const t of tiles) {
      const vIds = t.vertexIds;
      for (let i = 0; i < 6; i++) {
        const a = vIds[i];
        const b = vIds[(i + 1) % 6];
        const v1 = Math.min(a, b);
        const v2 = Math.max(a, b);
        const key = `${v1}_${v2}`;
        if (!edgeMap.has(key)) {
          const p1 = vertices[v1];
          const p2 = vertices[v2];
          edgeMap.set(key, { v1, v2, x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y });
        }
      }
    }

    // Convert edges to array, sort visually, then REINDEX ids to be continuous 0..71
    const edgeArr = Array.from(edgeMap.entries())
      .map(([key, e]) => ({ key, ...e, mx: (e.x1 + e.x2) / 2, my: (e.y1 + e.y2) / 2 }))
      .sort((a, b) => (a.my === b.my ? a.mx - b.mx : a.my - b.my));

    const keyToEdgeId = new Map<string, number>();
    edgeArr.forEach((e, idx) => {
      e.id = idx; // reindex
      e.owner = idx % 10 === 0 ? ((idx % 4) + 1) : null; // demo owners
      keyToEdgeId.set(e.key, idx);
    });

    const edges: Record<number, Edge> = Object.fromEntries(edgeArr.map((e) => [e.id, e as Edge]));

    // Attach edge ids back to tiles (no gaps guaranteed)
    tiles.forEach((t) => {
      t.edgeIds = t.vertexIds.map((_, i) => {
        const a = t.vertexIds[i];
        const b = t.vertexIds[(i + 1) % 6];
        const v1 = Math.min(a, b);
        const v2 = Math.max(a, b);
        return keyToEdgeId.get(`${v1}_${v2}`);
      });
    });

    return { tiles, vertices, edges };
  }, [hexesWithIds, size]);

  const [selectedTiles, setSelectedTiles] = useState<Set<number>>(new Set());
  const [selectedEdges, setSelectedEdges] = useState<Set<number>>(new Set());
  const [selectedVertices, setSelectedVertices] = useState<Set<number>>(new Set());
  const [lastClick, setLastClick] = useState<LastClick>(null);

  function toggleSetItem(setState: React.Dispatch<React.SetStateAction<Set<number>>>, item: number) {
    setState((prev: Set<number>) => {
      const next = new Set(prev);
      if (next.has(item)) next.delete(item);
      else next.add(item);
      return next;
    });
  }

  function handleTileClick(tile: Tile) {
    toggleSetItem(setSelectedTiles, tile.id);
    setLastClick({ type: "tile", id: tile.id });
  }

  function handleEdgeClick(edge: Edge) {
    toggleSetItem(setSelectedEdges, edge.id);
    setLastClick({ type: "edge", id: edge.id });
  }

  function handleVertexClick(vertex: Vertex) {
    toggleSetItem(setSelectedVertices, vertex.id);
    setLastClick({ type: "vertex", id: vertex.id });
  }

  const allX = geometry.tiles.map((t) => t.cx);
  const allY = geometry.tiles.map((t) => t.cy);
const PAD = size * 2; // tighter fit so it reaches the top
const minX = Math.min(...allX) - PAD;
const maxX = Math.max(...allX) + PAD;
const minY = Math.min(...allY) - PAD;
const maxY = Math.max(...allY) + PAD;
const width = maxX - minX;
const height = maxY - minY;


  return (

    <div className="w-full h-full">
      <svg
        viewBox={`${minX} ${minY} ${width} ${height}`}
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid meet"
        className="w-full h-full block"
      >

        <defs>
          <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="3" stdDeviation="3" floodOpacity="0.15" />
          </filter>
        </defs>

        {/* Background */}
        <rect
          x={minX}
          y={minY}
          width={width}
          height={height}
          fill="#2A66A0"
          pointerEvents="none"    // so clicks go through to tiles/edges
        />

        {/* Tiles */}
        <g>
          {geometry.tiles.map((tile) => {
            const isSel = selectedTiles.has(tile.id);
            const fillColor = RESOURCE_COLORS[tile.resource];
            return (
              <g key={tile.id}>
                <polygon
                  points={tile.pts.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill={isSel ? "#fde68a" : fillColor}
                  stroke="#374151"
                  strokeWidth={1}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    handleTileClick(tile);
                  }}
                  style={{ cursor: "pointer", filter: "url(#shadow)" }}
                />
                <text
                  x={tile.cx}
                  y={tile.cy + 6}
                  textAnchor="middle"
                  fontSize={16}
                  fill="#111827"
                  pointerEvents="none"
                >
                  {tile.id}
                </text>
                {tile.robber && (
                  <circle
                    cx={tile.cx}
                    cy={tile.cy - 15}
                    r={10}
                    fill="#000"
                    stroke="#fff"
                    strokeWidth={3}
                    pointerEvents="none"
                  />
                )}
              </g>
            );
          })}
        </g>

        {/* Edges without halo, just white */}
        <g>
          {Object.values(geometry.edges).map((e) => {
            const isSel = selectedEdges.has(e.id);
            const strokeColor = e.owner ? PLAYER_COLORS[e.owner] : "#ffffff"; // white if no owner

            return (
              <g key={e.id}>
                <line
                  x1={e.x1}
                  y1={e.y1}
                  x2={e.x2}
                  y2={e.y2}
                  stroke={isSel ? "#ef4444" : strokeColor}
                  strokeWidth={EDGE_STROKE}
                  strokeLinecap="round"
                  style={{ cursor: "pointer" }}
                  pointerEvents="stroke"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    handleEdgeClick(e);
                  }}
                />
                <text
                  x={(e.x1 + e.x2) / 2}
                  y={(e.y1 + e.y2) / 2}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#111827"
                  pointerEvents="none"
                >
                  {e.id}
                </text>
              </g>
            );
          })}
        </g>


        {/* Vertices */}
        <g>
          {Object.values(geometry.vertices).map((v) => {
            const isSel = selectedVertices.has(v.id);
            const fillColor = v.owner ? PLAYER_COLORS[v.owner] : "#fff";
            const strokeColor = "#111827";
            return (
              <g key={v.id}>
                {v.building === "City" ? (
                  <rect
                    x={v.x - 8}
                    y={v.y - 8}
                    width={16}
                    height={16}
                    fill={isSel ? "#60a5fa" : fillColor}
                    stroke={strokeColor}
                    strokeWidth={2}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      handleVertexClick(v);
                    }}
                    style={{ cursor: "pointer" }}
                  />
                ) : (
                  <circle
                    cx={v.x}
                    cy={v.y}
                    r={8}
                    fill={isSel ? "#60a5fa" : fillColor}
                    stroke={strokeColor}
                    strokeWidth={2}
                    onClick={(ev) => {
                      ev.stopPropagation();
                      handleVertexClick(v);
                    }}
                    style={{ cursor: "pointer" }}
                  />
                )}
                <text
                  x={v.x}
                  y={v.y - 12}
                  textAnchor="middle"
                  fontSize={12}
                  fill="#111827"
                  pointerEvents="none"
                >
                  {v.id}
                </text>
                {/* Port indicator */}
                {v.port && (
                  <g pointerEvents="none">
                    {(() => {
                      // Calculate text width (approximate) - smaller
                      const textWidth = v.port.length * 5 + 3;
                      const boxWidth = Math.max(textWidth, 16);

                      // Position closer to vertex
                      const offsetY = 18; // Reduced from 25 to 18

                      return (
                        <>
                          <rect
                            x={v.x - boxWidth / 2}
                            y={v.y + offsetY - 6}
                            width={boxWidth}
                            height={12}
                            rx={6}
                            fill="#1e40af"
                            stroke="#ffffff"
                            strokeWidth={1}
                          />
                          <text
                            x={v.x}
                            y={v.y + offsetY + 2}
                            textAnchor="middle"
                            fontSize={7}
                            fill="#ffffff"
                            fontWeight="bold"
                          >
                            {v.port}
                          </text>
                        </>
                      );
                    })()}
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}