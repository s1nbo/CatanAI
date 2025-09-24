// Board.tsx
// HexGrid React component (Plain React + Tailwind + CSS)
// Tiles: 0–18, Vertices: 0–53, Edges: 0–71
// Now supports "overlay" props to apply live server state.

import React, { useMemo, useState } from "react";

/** ---- Overlay types coming from server-normalized data ---- */
export type BoardOverlay = {
  tiles?: Array<{
    resource?: string | null;   // e.g., "Lumber" | "Grain" | "Wool" | "Brick" | "Ore" | "Desert"
    number?: number | null;     // 2..12 or null for Desert
    robber?: boolean | null;
  }>;
  vertices?: Array<{
    building?: "Settlement" | "City" | null;
    owner?: number | null;      // 1..4 or null
    port?: string | null;       // "3:1", "2:1 Brick", ...
  }>;
  edges?: Array<{
    owner?: number | null;      // 1..4 or null
  }>;
};

/** ---- Geometry Types (internal) ---- */
interface VertexG {
  id: number;
  x: number; y: number;
  building: string | null;
  owner: number | null;
  port: string | null;
  blocked: boolean;
}
interface EdgeG {
  id: number;
  v1: number; v2: number;
  x1: number; y1: number; x2: number; y2: number;
  mx: number; my: number;
  owner: number | null;
}
interface TileG {
  id: number;
  cx: number; cy: number;
  pts: { x: number; y: number; }[];
  keys: string[];
  vertexIds: number[];
  edgeIds: number[];
  resource: keyof typeof RESOURCE_COLORS;
  number: number | null;
  robber: boolean | null;
}
interface Geometry { tiles: TileG[]; vertices: Record<number, VertexG>; edges: Record<number, EdgeG>; }
type LastClick = { type: 'tile' | 'edge' | 'vertex'; id: number } | null;

const HEX_SIZE = 64;
const VERTEX_ROW_COUNTS = [7, 9, 11, 11, 9, 7];
const SNAP_K = 1000;
const EDGE_STROKE = 6;

// Darker, dimmed tile colors for better eye comfort
const RESOURCE_COLORS = {
  Wood: "#14532d",
  Brick: "#9a3412",
  Sheep: "#65a30d",
  Wheat: "#ca8a04",
  Ore: "#4b5563",
  Desert: "#e7e5e4",
  null: "#e5e7eb",
};

// Server → board color key
const RESOURCE_ALIASES: Record<string, keyof typeof RESOURCE_COLORS> = {
  Lumber: "Wood",
  Grain: "Wheat",
  Wool: "Sheep",
  Brick: "Brick",
  Ore: "Ore",
  Desert: "Desert",
  Wood: "Wood",
  Wheat: "Wheat",
  Sheep: "Sheep",
  null: "null",
};

// Player colors: orange, purple, dark blue, light blue
const PLAYER_COLORS: Record<number | "null", string> = {
  1: "#f97316",
  2: "#a855f7",
  3: "#1448d5",
  4: "#000000",
  null: "#374151",
};

function hexToPixel(q: number, r: number, size: number): { x: number; y: number } {
  const x = size * Math.sqrt(3) * (q + r / 2);
  const y = size * (3 / 2) * r;
  return { x, y };
}
function snap(v: number): number { return Math.round(v * SNAP_K) / SNAP_K; }
function vKey(x: number, y: number): string { return `${snap(x)}_${snap(y)}`; }

function generateHexes(radius: number): { q: number; r: number }[] {
  const hexes: { q: number; r: number }[] = [];
  for (let q = -radius; q <= radius; q++) {
    const r1 = Math.max(-radius, -q - radius);
    const r2 = Math.min(radius, -q + radius);
    for (let r = r1; r <= r2; r++) hexes.push({ q, r });
  }
  return hexes;
}

export default function HexBoard({
  radius = 2,
  size = HEX_SIZE,
  overlay,
}: {
  radius?: number;
  size?: number;
  overlay?: BoardOverlay;
}) {
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

    const vEntries = Object.entries(vertexIndex).sort(([, a], [, b]) => (a.y === b.y ? a.x - b.x : a.y - b.y));
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

    const vertices: Record<number, VertexG> = {};
    const keyToVid: Record<string, number> = {};
    let vid = 0;
    for (let r = 0; r < rows.length; r++) {
      const row = rows[r].slice().sort(([, a], [, b]) => a.x - b.x);
      for (const [k, v] of row) {
        vertices[vid] = {
          id: vid,
          x: v.x,
          y: v.y,
          building: null,
          owner: null,
          port: null,
          blocked: false,
        };
        keyToVid[k] = vid;
        vid++;
      }
    }

    const sampleResources: Array<keyof typeof RESOURCE_COLORS> = ["Wood", "Brick", "Sheep", "Wheat", "Ore", "Desert"];
    const tiles: TileG[] = tilesDraft.map((t, idx) => ({
      ...t,
      id: idx,
      vertexIds: t.keys.map((k) => keyToVid[k]),
      resource: sampleResources[idx % sampleResources.length],
      number: ((idx % 11) + 2), // placeholder, will be overridden by overlay
      robber: idx === 0 ? true : null,
      edgeIds: [],
      keys: t.keys,
    }));

    // Build unique edges
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

    const edgeArr = Array.from(edgeMap.entries())
      .map(([key, e]) => ({ key, ...e, mx: (e.x1 + e.x2) / 2, my: (e.y1 + e.y2) / 2 }))
      .sort((a, b) => (a.my === b.my ? a.mx - b.mx : a.my - b.my));

    const keyToEdgeId = new Map<string, number>();
    edgeArr.forEach((e, idx) => {
      e.id = idx;
      e.owner = null; // placeholder; overlay will control
      keyToEdgeId.set(e.key, idx);
    });

    const edges: Record<number, EdgeG> = Object.fromEntries(edgeArr.map((e) => [e.id, e as EdgeG]));

    tiles.forEach((t) => {
      t.edgeIds = t.vertexIds.map((_, i) => {
        const a = t.vertexIds[i];
        const b = t.vertexIds[(i + 1) % 6];
        const v1 = Math.min(a, b);
        const v2 = Math.max(a, b);
        return keyToEdgeId.get(`${v1}_${v2}`)!;
      });
    });

    return { tiles, vertices, edges };
  }, [hexesWithIds, size]);

  // Selection UI (unchanged)
  const [selectedTiles, setSelectedTiles] = useState<Set<number>>(new Set());
  const [selectedEdges, setSelectedEdges] = useState<Set<number>>(new Set());
  const [selectedVertices, setSelectedVertices] = useState<Set<number>>(new Set());
  const [lastClick, setLastClick] = useState<LastClick>(null);
  function toggleSetItem(setState: React.Dispatch<React.SetStateAction<Set<number>>>, item: number) {
    setState((prev) => {
      const next = new Set(prev);
      if (next.has(item)) next.delete(item);
      else next.add(item);
      return next;
    });
  }
  function handleTileClick(tile: TileG) { toggleSetItem(setSelectedTiles, tile.id); setLastClick({ type: "tile", id: tile.id }); }
  function handleEdgeClick(edge: EdgeG) { toggleSetItem(setSelectedEdges, edge.id); setLastClick({ type: "edge", id: edge.id }); }
  function handleVertexClick(vertex: VertexG) { toggleSetItem(setSelectedVertices, vertex.id); setLastClick({ type: "vertex", id: vertex.id }); }

  const allX = geometry.tiles.map((t) => t.cx);
  const allY = geometry.tiles.map((t) => t.cy);
  const PAD = size * 2;
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
        <rect x={minX} y={minY} width={width} height={height} fill="#2A66A0" pointerEvents="none" />

        {/* Tiles */}
        <g>
          {geometry.tiles.map((tile) => {
            const ov = overlay?.tiles?.[tile.id];
            const resKey = ov?.resource != null
              ? (RESOURCE_ALIASES[ov.resource as string] ?? "null")
              : tile.resource;
            const isSel = selectedTiles.has(tile.id);
            const fillColor = RESOURCE_COLORS[resKey as keyof typeof RESOURCE_COLORS];

            const number = (ov?.number ?? tile.number) ?? null;
            const robber = ov?.robber ?? tile.robber;

            return (
              <g key={tile.id}>
                <polygon
                  points={tile.pts.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill={isSel ? "#fde68a" : fillColor}
                  stroke="#374151"
                  strokeWidth={1}
                  onClick={(ev) => { ev.stopPropagation(); handleTileClick(tile); }}
                  style={{ cursor: "pointer", filter: "url(#shadow)" }}
                />
                {/* Tile ID (small) */}
                <text x={tile.cx} y={tile.cy + 22} textAnchor="middle" fontSize={10} fill="#111827" pointerEvents="none">
                  #{tile.id}
                </text>
                {/* Number token */}
                {number && (
                  <g>
                    <circle cx={tile.cx} cy={tile.cy - 2} r={14} fill="#fff" stroke="#111827" strokeWidth={1.5} />
                    <text x={tile.cx} y={tile.cy + 3} textAnchor="middle" fontSize={12} fontWeight={700} fill="#111827" pointerEvents="none">
                      {number}
                    </text>
                  </g>
                )}
                {/* Robber */}
                {robber && (
                  <circle cx={tile.cx} cy={tile.cy - 22} r={9} fill="#000" stroke="#fff" strokeWidth={2} pointerEvents="none" />
                )}
              </g>
            );
          })}
        </g>

        {/* Edges (owner colored or white) */}
        <g>
          {Object.values(geometry.edges).map((e) => {
            const ov = overlay?.edges?.[e.id];
            const owner = ov?.owner ?? e.owner ?? null;
            const isSel = selectedEdges.has(e.id);
            const strokeColor = owner ? PLAYER_COLORS[owner] : "#ffffff";

            return (
              <g key={e.id}>
                <line
                  x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
                  stroke={isSel ? "#ef4444" : strokeColor}
                  strokeWidth={EDGE_STROKE}
                  strokeLinecap="round"
                  style={{ cursor: "pointer" }}
                  pointerEvents="stroke"
                  onClick={(ev) => { ev.stopPropagation(); handleEdgeClick(e); }}
                />
                <text x={(e.x1 + e.x2) / 2} y={(e.y1 + e.y2) / 2} textAnchor="middle" fontSize={10} fill="#111827" pointerEvents="none">
                  {e.id}
                </text>
              </g>
            );
          })}
        </g>

        {/* Vertices */}
        <g>
          {Object.values(geometry.vertices).map((v) => {
            const ov = overlay?.vertices?.[v.id];
            const building = (ov?.building ?? v.building) as "City" | "Settlement" | null;
            const owner = ov?.owner ?? v.owner;
            const port = ov?.port ?? v.port;

            const isSel = selectedVertices.has(v.id);
            const fillColor = owner ? PLAYER_COLORS[owner] : "#fff";
            const strokeColor = "#111827";

            return (
              <g key={v.id}>
                {building === "City" ? (
                  <rect
                    x={v.x - 8} y={v.y - 8} width={16} height={16}
                    fill={isSel ? "#60a5fa" : fillColor}
                    stroke={strokeColor} strokeWidth={2}
                    onClick={(ev) => { ev.stopPropagation(); handleVertexClick(v); }}
                    style={{ cursor: "pointer" }}
                  />
                ) : (
                  <circle
                    cx={v.x} cy={v.y} r={8}
                    fill={isSel ? "#60a5fa" : fillColor}
                    stroke={strokeColor} strokeWidth={2}
                    onClick={(ev) => { ev.stopPropagation(); handleVertexClick(v); }}
                    style={{ cursor: "pointer" }}
                  />
                )}
                <text x={v.x} y={v.y - 12} textAnchor="middle" fontSize={12} fill="#111827" pointerEvents="none">
                  {v.id}
                </text>
                {port && (
                  <g pointerEvents="none">
                    {(() => {
                      const textWidth = port.length * 5 + 3;
                      const boxWidth = Math.max(textWidth, 16);
                      const offsetY = 18;
                      return (
                        <>
                          <rect x={v.x - boxWidth / 2} y={v.y + offsetY - 6} width={boxWidth} height={12} rx={6} fill="#1e40af" stroke="#ffffff" strokeWidth={1} />
                          <text x={v.x} y={v.y + offsetY + 2} textAnchor="middle" fontSize={7} fill="#ffffff" fontWeight="bold">
                            {port}
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
