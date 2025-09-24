// App.tsx
import { useState, useMemo, useEffect, useRef } from "react";
import {
  Trophy, Swords, Route, Hand, Layers,
  Dice5, ShoppingBag, Handshake
} from "lucide-react";
import "./App.css";
import HexBoard from "./Board";
import type { BoardOverlay } from "./Board";


// Add under your imports:
type SelfPanel = {
  id: string;
  name: string;
  color: string;
  victoryPoints: number;
  resources: { wood: number; brick: number; sheep: number; wheat: number; ore: number };
  devList: string[];   // non-VP devs (playable)
  vpCards: number;     // VP development cards
};

// Try to detect my player id from env or WS URL later
const DEFAULT_SELF_FROM_ENV = (import.meta as any).env?.VITE_PLAYER_ID ?? null;

// Flexible normalizers (server schemas vary)
function normalizeResources(raw: any): SelfPanel["resources"] {
  // Accept raw.resources, raw.hand, or flat counts
  const src = raw?.resources ?? raw?.hand ?? raw ?? {};
  const n = (v: any) => (typeof v === "number" ? v : 0);
  return {
    wood: n(src.wood ?? src.Wood),
    brick: n(src.brick ?? src.Brick),
    sheep: n(src.sheep ?? src.Sheep ?? src.wool ?? src.Wool),
    wheat: n(src.wheat ?? src.Wheat ?? src.grain ?? src.Grain),
    ore: n(src.ore ?? src.Ore),
  };
}

function normalizeDevCards(raw: any): { devList: string[]; vpCards: number } {
  // Accept array, counts map, or fields
  const out: string[] = [];
  let vp = 0;

  const arr = raw?.development_cards ?? raw?.dev_cards ?? null;
  const counts = raw?.development_cards_counts ?? raw?.dev_cards_counts ?? null;

  if (Array.isArray(arr)) {
    for (const d of arr) {
      const name = String(d);
      if (/victory/i.test(name)) vp += 1; else out.push(name);
    }
  } else if (counts && typeof counts === "object") {
    const pushTimes = (label: string, times: number) => { for (let i = 0; i < (times || 0); i++) out.push(label); };
    pushTimes("Knight", counts.Knight ?? counts.knight);
    pushTimes("Road Building", counts["Road Building"] ?? counts.road_building);
    pushTimes("Year of Plenty", counts["Year of Plenty"] ?? counts.year_of_plenty);
    pushTimes("Monopoly", counts.Monopoly ?? counts.monopoly);
    vp = (counts["Victory Point"] ?? counts.victory_point ?? 0) as number;
  } else {
    // Fallback to totals only if exposed
    vp = raw?.victory_point_cards ?? raw?.vp_cards ?? 0;
    // If only total devs is provided, we can’t know their types → leave out[]
  }

  // Sometimes server sends total_development_cards AND a list—prefer list, but ensure count doesn’t exceed total.
  const total = raw?.total_development_cards;
  if (typeof total === "number" && out.length + vp > total) {
    // Trim extras defensively
    const overflow = out.length + vp - total;
    out.splice(0, Math.max(0, overflow));
  }

  return { devList: out, vpCards: vp };
}

function extractSelfPanel(playersMap: Record<string, any>, selfId: string, playerColors: Record<string, string>): SelfPanel {
  const raw = (playersMap && playersMap[selfId]) ? (typeof playersMap[selfId] === "string" ? JSON.parse(playersMap[selfId]) : playersMap[selfId]) : {};
  const resources = normalizeResources(raw);
  const { devList, vpCards } = normalizeDevCards(raw);
  const victoryPoints = raw?.victory_points ?? 0;
  const name = `Player ${selfId}`;
  const color = playerColors[selfId] ?? "#94a3b8";

  return { id: selfId, name, color, victoryPoints, resources, devList, vpCards };
}


/** ---------- Types for UI state ---------- */
type Player = {
  id: string;           // "1" | "2" | ...
  name: string;         // "Player 1" etc
  color: string;
  victoryPoints: number;
  largestArmy: number;  // 0/1 display
  longestRoad: number;  // 0/1 display
  cities: number;
  settlements: number;
  roads: number;
  handSize: number;
  devCards: number;
  isCurrent?: boolean;
};

type Bank = {
  wood: number;
  brick: number;
  sheep: number;
  wheat: number;
  ore: number;
  devCards: number;
};

/** ---------- Color palette for players ---------- */
const PLAYER_COLORS: Record<string, string> = {
  "1": "#f97316",
  "2": "#a855f7",
  "3": "#1448d5",
  "4": "#000000",
};

/** ---------- Dev card emoji for HUD ---------- */
const DEV_EMOJI: Record<string, string> = {
  "Knight": "⚔️",
  "Road Building": "🛣️",
  "Year of Plenty": "🎁",
  "Monopoly": "🎩",
};
const DIE = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];

/** ---------- Helper: parse possibly-stringified player object ---------- */
function parseMaybeJSONString<T = any>(v: any): T {
  if (typeof v === "string") {
    try { return JSON.parse(v) as T; } catch { return v as T; }
  }
  return v as T;
}

/** ---------- Helper: normalize server payload into UI + overlay ---------- */
function toOverlayFromServer(server: any): {
  overlay: BoardOverlay;
  players: Player[];
  bank: Bank;
} {
  const overlay: BoardOverlay = {
    tiles: [],
    edges: [],
    vertices: [],
  };

  // --- Tiles
  if (Array.isArray(server?.board?.tiles)) {
    overlay.tiles = server.board.tiles.map((t: any) => ({
      resource: t.resource ?? null,
      number: t.number ?? null,
      robber: !!t.robber,
    }));
  }

  // --- Edges
  if (Array.isArray(server?.board?.edges)) {
    overlay.edges = server.board.edges.map((e: any) => ({
      owner: e.player ?? null,
    }));
  }

  // --- Vertices
  if (Array.isArray(server?.board?.vertices)) {
    overlay.vertices = server.board.vertices.map((v: any) => ({
      building: v.building ?? null, // "Settlement" | "City" | null
      owner: v.player ?? null,
      port: v.port ?? null,
    }));
  }

  // --- Bank + dev deck
  const bank: Bank = {
    wood: server?.bank?.wood ?? 0,
    brick: server?.bank?.brick ?? 0,
    sheep: server?.bank?.sheep ?? 0,
    wheat: server?.bank?.wheat ?? 0,
    ore: server?.bank?.ore ?? 0,
    devCards: server?.development_cards_remaining ?? 0,
  };

  // --- Players

  const playersMap = server?.players ?? {};
  // handle both spellings just in case
  const placementRaw =
    server?.initial_placement_order ??
    server?.inital_placement_order ??
    null;

  // decide who to highlight
  let highlightId: string | null = null;
  if (placementRaw !== null && placementRaw !== undefined && Number(placementRaw) !== -1) {
    highlightId = String(placementRaw);
  } else if (server?.current_turn !== null && server?.current_turn !== undefined) {
    highlightId = String(server.current_turn);
  }

  const ids = Object.keys(playersMap).sort((a, b) => Number(a) - Number(b));
  const players: Player[] = ids.map((pid) => {
    const raw = parseMaybeJSONString(playersMap[pid]) as any;
    const name = `Player ${pid}`;
    const color = PLAYER_COLORS[pid] ?? "#94a3b8";
    return {
      id: pid,
      name,
      color,
      victoryPoints: raw?.victory_points ?? 0,
      largestArmy: raw?.largest_army ? 1 : 0,
      longestRoad: raw?.longest_road ? 1 : 0,
      cities: raw?.cities ?? 0,
      settlements: raw?.settlements ?? 0,
      roads: raw?.roads ?? 0,
      handSize: raw?.total_hand ?? 0,
      devCards: raw?.total_development_cards ?? 0,
      // highlight logic here:
      isCurrent: highlightId === String(pid),
    };
  });

  return { overlay, players, bank };
}

export default function App() {
  // ---- Live state (initial placeholders) ----
  const [players, setPlayers] = useState<Player[]>([
    { id: "1", name: "Player 1", color: PLAYER_COLORS["1"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "2", name: "Player 2", color: PLAYER_COLORS["2"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "3", name: "Player 3", color: PLAYER_COLORS["3"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "4", name: "Player 4", color: PLAYER_COLORS["4"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
  ]);
  const [bank, setBank] = useState<Bank>({ wood: 19, brick: 19, sheep: 19, wheat: 19, ore: 19, devCards: 25 });
  const [overlay, setOverlay] = useState<BoardOverlay>({ tiles: [], edges: [], vertices: [] });

  const [selfId, setSelfId] = useState<string | null>(DEFAULT_SELF_FROM_ENV);
const [self, setSelf] = useState<SelfPanel>({
  id: selfId ?? "1",
  name: `Player ${selfId ?? "1"}`,
  color: PLAYER_COLORS[selfId ?? "1"] ?? "#94a3b8",
  victoryPoints: 0,
  resources: { wood: 0, brick: 0, sheep: 0, wheat: 0, ore: 0 },
  devList: [],
  vpCards: 0,
});

  // ---- HUD (your-hand) placeholders; wire to server later if needed ----
  const [playableDevCards, setPlayableDevCards] = useState<string[]>(["Knight", "Knight", "Knight", "Road Building", "Year of Plenty", "Monopoly"]);
  const [vpCards, setVpCards] = useState<number>(1);
  const [resources, setResources] = useState<{ wood: number; brick: number; sheep: number; wheat: number; ore: number; }>(
    { wood: 2, brick: 1, sheep: 3, wheat: 0, ore: 2 }
  );

  // ---- Dice roll from server ----
  const [currentRoll, setCurrentRoll] = useState<{ d1: number; d2: number } | null>(null);
  const [isRolling, setIsRolling] = useState(false);
  function onServerRolled(d1: number, d2: number) { setCurrentRoll({ d1, d2 }); setIsRolling(false); }

  // Expose a quick dev hook to simulate dice
  if (typeof window !== "undefined") {
    (window as any).simRoll = (d1: number, d2: number) => onServerRolled(d1, d2);
  }

  function handleRollDice() {
    setIsRolling(true);
    // TODO: send a "roll" action over WS if your server expects it
  }
  function handleTrade() { /* TODO */ }
  function handleBuyDev() { /* TODO */ }
  function playDev(type: string) {
    setPlayableDevCards(prev => {
      const idx = prev.indexOf(type);
      if (idx === -1) return prev;
      const next = prev.slice(); next.splice(idx, 1); return next;
    });
  }

  const devGroups = useMemo(() => {
    const counts = new Map<string, number>();
    playableDevCards.forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
    return Array.from(counts.entries()).map(([type, count]) => ({ type, count }));
  }, [playableDevCards]);

  // ---- WebSocket wiring ----
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    const url =
  (import.meta as any).env?.VITE_WS_URL ??
  `ws://localhost:8000/ws/1/1`; // ws://.../ws/{game_id}/{player_id}

if (!selfId) {
  try {
    const pid = new URL(url).pathname.split("/").filter(Boolean).pop(); // last segment
    if (pid) setSelfId(pid);
  } catch {}
}

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Optionally identify / subscribe, depending on your backend protocol
        // ws.send(JSON.stringify({ type: "subscribe_state" }));
      };

      ws.onmessage = (ev) => {
        let data: any;
        try { data = JSON.parse(ev.data); } catch { data = ev.data; }

        // Possible message types:
        // 1) Full game snapshot (board/players/bank/etc.)
        if (data?.board && data?.players) {
          const { overlay, players, bank } = toOverlayFromServer(data);
          setOverlay(overlay);
          setPlayers(players);
          setBank(bank);
          return;
        }

        // 2) Dice roll event
        if (data?.type === "roll" && typeof data?.d1 === "number" && typeof data?.d2 === "number") {
          onServerRolled(data.d1, data.d2);
          return;
        }

        // 3) Lightweight patches could be handled here (optional)
      };

      ws.onerror = () => { /* you may surface a toast/log */ };
      ws.onclose = () => { /* optionally handle reconnect */ };
      return () => { ws.close(); };
    } catch {
      // Silently ignore in environments without WS
    }
  }, []);

  // Dev helper: allow manual injection of a server snapshot (e.g., paste server.json in console)
  useEffect(() => {
    if (typeof window === "undefined") return;
    (window as any).applyServer = (snap: any) => {
      const { overlay, players, bank } = toOverlayFromServer(snap);
      setOverlay(overlay);
      setPlayers(players);
      setBank(bank);
    };
  }, []);

  return (
    <div className="layout">
      {/* Left: board area with in-board HUD */}
      <div className="board">
        {/* LEFT HUD overlay */}
        <div className="hud-left">
          {/* Actions */}
          <div className="hud-card">
            <h3 className="hud-title">Actions</h3>
            <div className="actions-grid">
              <button onClick={handleRollDice} title="Roll Dice" disabled={isRolling}>
                <Dice5 size={18} /> {isRolling ? "Rolling…" : "Roll"}
              </button>
              <button onClick={handleTrade} title="Trade">
                <Handshake size={18} /> Trade
              </button>
              <button onClick={handleBuyDev} title="Buy Dev">
                <ShoppingBag size={18} /> Buy
              </button>
            </div>

            <div className="roll-row">
              <span className="roll-label">Current roll</span>
              <span className="roll-pill">
                <span className="roll-dice">
                  {currentRoll ? `${DIE[currentRoll.d1]} ${DIE[currentRoll.d2]}` : "— —"}
                </span>
                <span>{currentRoll ? currentRoll.d1 + currentRoll.d2 : "—"}</span>
              </span>
            </div>
          </div>

          {/* Development Cards (playable) */}
          <div className="dev-row">
            {devGroups.map(({ type, count }) => (
              <div
                key={type}
                className="dev-card"
                onClick={() => playDev(type)}
                title={`${type} ×${count}`}
                aria-label={`${type} ${count}`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && playDev(type)}
              >
                <span className="dev-emoji">{DEV_EMOJI[type] ?? "🎴"}</span>
                {count > 1 && <span className="dev-badge">{count}</span>}
              </div>
            ))}
            {playableDevCards.length === 0 && <div style={{ opacity: .7 }}>No playable cards</div>}
          </div>

          {/* Victory Point Cards */}
          <div className="hud-card">
            <h3 className="hud-title">Victory Points</h3>
            <div className="vp-stack">
              <div className="vp-badge">VP</div>
              <div><strong>{vpCards}</strong> card{vpCards === 1 ? "" : "s"}</div>
            </div>
          </div>

          {/* Resources (client player's hand; keep placeholder for now) */}
          <div className="hud-card">
            <h3 className="hud-title">Resources</h3>
            <div className="resource-grid">
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🌲</span></div><div className="count-pill">{resources.wood}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🧱</span></div><div className="count-pill">{resources.brick}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🐑</span></div><div className="count-pill">{resources.sheep}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🌾</span></div><div className="count-pill">{resources.wheat}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">⛰️</span></div><div className="count-pill">{resources.ore}</div></div>
            </div>
          </div>
        </div>

        {/* Board (now driven by overlay) */}
        <HexBoard overlay={overlay} />
      </div>

      {/* Right: sidebar (Bank + Players) */}
      <aside className="sidebar">
        <div className="card">
          <h2 className="card-title">Bank</h2>
          <div className="bank-grid">
            <div>🌲 Wood: <strong>{bank.wood}</strong></div>
            <div>🧱 Brick: <strong>{bank.brick}</strong></div>
            <div>🐑 Sheep: <strong>{bank.sheep}</strong></div>
            <div>🌾 Wheat: <strong>{bank.wheat}</strong></div>
            <div>⛰️ Ore: <strong>{bank.ore}</strong></div>
            <div>🎴 Dev Cards: <strong>{bank.devCards}</strong></div>
          </div>
        </div>

        <h2 className="section-title">Players</h2>
        {players.map((p) => (
          <div className="card" key={p.id} style={p.isCurrent ? { outline: `2px solid ${p.color}` } : undefined}>
            <div className="player-header">
              <div className="dot" style={{ backgroundColor: p.color }} />
              <span className="player-name">{p.name}</span>
            </div>
            <div className="stats-grid">
              <div className="stat"><Trophy /> <span>{p.victoryPoints}</span></div>
              <div className="stat"><Swords /> <span>{p.largestArmy}</span></div>
              <div className="stat"><Route /> <span>{p.longestRoad}</span></div>
              <div className="stat"><Hand /> <span>{p.handSize}</span></div>
              <div className="stat"><Layers /> <span>{p.devCards}</span></div>
            </div>
            <div className="stats-grid" style={{ marginTop: 4, opacity: .8, fontSize: 12 }}>
              <div>🏘️ Settlements: <strong>{p.settlements}</strong></div>
              <div>🏙️ Cities: <strong>{p.cities}</strong></div>
              <div>🛣️ Roads: <strong>{p.roads}</strong></div>
            </div>
          </div>
        ))}
      </aside>
    </div>
  );
}
