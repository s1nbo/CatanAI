// Board.tsx
// HexGrid React component (Plain React + Tailwind + CSS)
// Tiles: 0–18, Vertices: 0–53, Edges: 0–71
// Now supports "overlay" props to apply live server state and emits click events for actions.

import React, { useMemo, useState } from "react";

/** ---- Overlay types coming from server-normalized data ---- */
export type BoardOverlay = {
  tiles?: Array<{
    resource?: string | null;   // e.g., "Wood" | "Wheat" | "Sheep" | "Brick" | "Ore" | "Desert"
    number?: number | null;     // 2..12 or null for Desert
    robber?: boolean | null;
  }>;
  vertices?: Array<{
    building?: string | null;   // server might send "settlement"/"city"
    owner?: number | null;      // 1..4 or null
    port?: string | null;       // "3:1", "2:1 Brick", ...
  }>;
  edges?: Array<{
    owner?: number | null;      // 1..4 or null
  }>;
};

/** ---- Click payloads (exported to App) ---- */
export type ClickVertexPayload = { id: number; owner: number | null; building: string | null };
export type ClickEdgePayload = { id: number; owner: number | null };

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
const EDGE_HIT_EXTRA = 8;

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
  Wood: "Wood",
  Brick: "Brick",
  Sheep: "Sheep",
  Wheat: "Wheat",
  Ore: "Ore",
  Desert: "Desert",
  
  
  null: "null",
};

// Player colors: orange, purple, dark blue, light blue
const PLAYER_COLORS: Record<number | "null", string> = {
  1: "#f97316",
  2: "#a855f7",
  3: "#003049",
  4: "#780000",
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
  onVertexClick,
  onEdgeClick,
  onSelect,
}: {
  radius?: number;
  size?: number;
  overlay?: BoardOverlay;
  onVertexClick?: (p: ClickVertexPayload) => void;
  onEdgeClick?: (p: ClickEdgePayload) => void;
  onSelect?: (sel: LastClick) => void;
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
      const pts = [] as { x: number; y: number }[];
      const keys = [] as string[];
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
      const sliced: typeof rows = [];
      let cursor = 0;
      for (const count of VERTEX_ROW_COUNTS) {
        sliced.push(vEntries.slice(cursor, cursor + count) as any);
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
      (e as any).id = idx;
      (e as any).owner = null; // placeholder; overlay will control
      keyToEdgeId.set(e.key, idx);
    });

    const edges: Record<number, EdgeG> = Object.fromEntries(edgeArr.map((e) => [(e as any).id, e as unknown as EdgeG]));

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


  // Single, mutually exclusive selection (tile OR edge OR vertex)
  const [selected, setSelected] = useState<LastClick>(null);
  const isSelected = (t: NonNullable<LastClick>["type"], id: number) =>
    selected?.type === t && selected?.id === id;
  const pick = (next: NonNullable<LastClick>) => {
    setSelected((prev) => {
      const same = prev && prev.type === next.type && prev.id === next.id;
      const updated = same ? null : next;
      onSelect?.(updated);     // NEW: bubble up
      return updated;
    });
  };

  // NOTE: in addition to selection, we emit a concise payload to parent for WS action
  function handleTileClick(tile: TileG) {
    pick({ type: "tile", id: tile.id });
  }
  function handleEdgeClick(edge: EdgeG) {
    pick({ type: "edge", id: edge.id });
    const ov = overlay?.edges?.[edge.id];
    const owner = ov?.owner ?? edge.owner ?? null;
    onEdgeClick?.({ id: edge.id, owner });
  }
  function handleVertexClick(vertex: VertexG) {
    pick({ type: "vertex", id: vertex.id });
    const ov = overlay?.vertices?.[vertex.id];
    const owner = ov?.owner ?? vertex.owner ?? null;
    const buildingRaw = ov?.building ?? vertex.building ?? null;
    onVertexClick?.({ id: vertex.id, owner, building: (buildingRaw == null ? null : String(buildingRaw)) });
  }

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
        onClick={() => { setSelected(null); onSelect?.(null); }}
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
            const isSel = isSelected("tile", tile.id);
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
            const isSel = isSelected("edge", e.id);
            const strokeColor = owner ? PLAYER_COLORS[owner] : "#ffffff";

            return (
              <g key={e.id}>
                <line
                  x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
                  stroke="transparent"
                  strokeWidth={EDGE_STROKE + EDGE_HIT_EXTRA}
                  strokeLinecap="round"
                  pointerEvents="stroke"
                  onClick={(ev) => { ev.stopPropagation(); handleEdgeClick(e); }}
                />
                <line
                  x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2}
                  stroke={isSel ? "#fde68a" : strokeColor}
                  strokeWidth={EDGE_STROKE}
                  strokeLinecap="round"
                  style={{ cursor: "pointer" }}
                  pointerEvents="stroke"
                  onClick={(ev) => { ev.stopPropagation(); handleEdgeClick(e); }}
                />
              </g>
            );
          })}
        </g>

        {/* Vertices */}
        <g>
          {Object.values(geometry.vertices).map((v) => {
            const ov = overlay?.vertices?.[v.id];
            const buildingRaw = (ov?.building ?? v.building) as string | null; // server may send lowercase
            const buildingLower = buildingRaw ? buildingRaw.toLowerCase() : null;
            const owner = ov?.owner ?? v.owner;
            const port = ov?.port ?? v.port;

            const isSel = isSelected("vertex", v.id);
            const fillColor = owner ? PLAYER_COLORS[owner] : "#fff";
            const strokeColor = "#111827";

            return (
              <g key={v.id}>
                {buildingLower === "city" ? (
                  <rect
                    x={v.x - 8} y={v.y - 8} width={16} height={16}
                    fill={isSel ? "#fde68a" : fillColor}
                    stroke={strokeColor} strokeWidth={2}
                    onClick={(ev) => { ev.stopPropagation(); handleVertexClick(v); }}
                    style={{ cursor: "pointer" }}
                  />
                ) : (
                  <circle
                    cx={v.x} cy={v.y} r={8}
                    fill={isSel ? "#fde68a" : fillColor}
                    stroke={strokeColor} strokeWidth={2}
                    onClick={(ev) => { ev.stopPropagation(); handleVertexClick(v); }}
                    style={{ cursor: "pointer" }}
                  />
                )}
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
