// App.tsx
import { useState, useMemo, useEffect, useRef } from "react";
import {
  Trophy, Swords, Route, Hand, Layers,
  Dice5, ShoppingBag, Handshake
} from "lucide-react";
import "./App.css";
import HexBoard from "./Board";
import type { BoardOverlay } from "./Board";

/** ---------- Types ---------- */
type Player = {
  id: string;
  name: string;
  color: string;
  victoryPoints: number;
  largestArmy: number;
  longestRoad: number;
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

type SelfPanel = {
  id: string;
  name: string;
  color: string;
  victoryPoints: number;
  resources: { wood: number; brick: number; sheep: number; wheat: number; ore: number };
  devList: string[];   // playable (non-VP) dev cards
  vpCards: number;     // VP development cards
};

/** ---------- Constants ---------- */
const PLAYER_COLORS: Record<string, string> = {
  "1": "#f97316", // orange
  "2": "#a855f7", // purple
  "3": "#1448d5", // dark blue
  "4": "#60a5fa", // light blue
};
const DIE = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];
const DEFAULT_SELF_FROM_ENV = (import.meta as any).env?.VITE_PLAYER_ID ?? null;

/** ---------- Helpers ---------- */
function parseMaybeJSONString<T = any>(v: any): T {
  if (typeof v === "string") {
    try { return JSON.parse(v) as T; } catch { return v as T; }
  }
  return v as T;
}

// Does this player entry look like the controlling client (has private info)?
function looksLikeSelfEntry(raw: any): boolean {
  if (!raw || typeof raw !== "object") return false;

  // Direct hand fields or nested hand/resources object
  const hasHandObj = !!(raw.resources || raw.hand);
  // Flat resource keys (common in some servers)
  const hasFlatResourceCounts =
    ["wood","brick","sheep","wheat","ore","Wood","Brick","Sheep","Wheat","Ore","grain","Grain","wool","Wool"]
      .some(k => typeof raw[k] === "number");

  // Dev cards as list or detailed counts (NOT just a total)
  const hasDevList = Array.isArray(raw.development_cards) || Array.isArray(raw.dev_cards);
  const hasDevCounts = !!(raw.development_cards_counts || raw.dev_cards_counts);

  // If any of these are present, assume this is the client's player
  return !!(hasHandObj || hasFlatResourceCounts || hasDevList || hasDevCounts);
}

function normalizeResources(raw: any): SelfPanel["resources"] {
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
    vp = raw?.victory_point_cards ?? raw?.vp_cards ?? 0;
  }

  const total = raw?.total_development_cards;
  if (typeof total === "number" && out.length + vp > total) {
    const overflow = out.length + vp - total;
    out.splice(0, Math.max(0, overflow));
  }

  return { devList: out, vpCards: vp };
}

function extractSelfPanel(playersMap: Record<string, any>, selfId: string, playerColors: Record<string, string>): SelfPanel {
  const rawEntry = playersMap?.[selfId];
  const raw = rawEntry ? (typeof rawEntry === "string" ? JSON.parse(rawEntry) : rawEntry) : {};
  const resources = normalizeResources(raw);
  const { devList, vpCards } = normalizeDevCards(raw);
  const victoryPoints = raw?.victory_points ?? 0;
  const name = `Player ${selfId}`;
  const color = playerColors[selfId] ?? "#94a3b8";
  return { id: selfId, name, color, victoryPoints, resources, devList, vpCards };
}

// Find controlling player ID from a snapshot by scanning for private info
function detectSelfFromSnapshot(server: any, fallback: string | null): string {
  const playersMap = server?.players ?? {};
  for (const [pid, entry] of Object.entries(playersMap)) {
    const raw = parseMaybeJSONString(entry);
    if (looksLikeSelfEntry(raw)) return String(pid);
  }
  // Secondary hints provided by server
  const hinted = server?.self_player_id ?? server?.you_are ?? null;
  if (hinted != null) return String(hinted);
  // Otherwise, use fallback (env/URL) or default to "1"
  return String(fallback ?? "1");
}

/** Highlight logic: prefer initial_placement_order if not -1, else current_turn */
function computeHighlightId(server: any): string | null {
  const placementRaw =
    server?.initial_placement_order ??
    server?.inital_placement_order ?? // tolerate misspelling
    null;

  if (placementRaw !== null && placementRaw !== undefined && Number(placementRaw) !== -1) {
    return String(placementRaw);
  }
  if (server?.current_turn !== null && server?.current_turn !== undefined) {
    return String(server.current_turn);
  }
  return null;
}

/** ---------- Server → UI normalize ---------- */
function toOverlayFromServer(server: any): {
  overlay: BoardOverlay;
  players: Player[];
  bank: Bank;
} {
  const overlay: BoardOverlay = { tiles: [], edges: [], vertices: [] };

  if (Array.isArray(server?.board?.tiles)) {
    overlay.tiles = server.board.tiles.map((t: any) => ({
      resource: t.resource ?? null,
      number: t.number ?? null,
      robber: !!t.robber,
    }));
  }
  if (Array.isArray(server?.board?.edges)) {
    overlay.edges = server.board.edges.map((e: any) => ({
      owner: e.player ?? null,
    }));
  }
  if (Array.isArray(server?.board?.vertices)) {
    overlay.vertices = server.board.vertices.map((v: any) => ({
      building: v.building ?? null,
      owner: v.player ?? null,
      port: v.port ?? null,
    }));
  }

  const bank: Bank = {
    wood: server?.bank?.wood ?? 0,
    brick: server?.bank?.brick ?? 0,
    sheep: server?.bank?.sheep ?? 0,
    wheat: server?.bank?.wheat ?? 0,
    ore: server?.bank?.ore ?? 0,
    devCards: server?.development_cards_remaining ?? 0,
  };

  const playersMap = server?.players ?? {};
  const highlightId = computeHighlightId(server);

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
      isCurrent: highlightId === String(pid),
    };
  });

  return { overlay, players, bank };
}

/** ---------- Component ---------- */
export default function App() {
  // Players/Bank/Board overlay
  const [players, setPlayers] = useState<Player[]>([
    { id: "1", name: "Player 1", color: PLAYER_COLORS["1"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "2", name: "Player 2", color: PLAYER_COLORS["2"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "3", name: "Player 3", color: PLAYER_COLORS["3"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "4", name: "Player 4", color: PLAYER_COLORS["4"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
  ]);
  const [bank, setBank] = useState<Bank>({ wood: 19, brick: 19, sheep: 19, wheat: 19, ore: 19, devCards: 25 });
  const [overlay, setOverlay] = useState<BoardOverlay>({ tiles: [], edges: [], vertices: [] });

  // Self (controlling player)
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

  // Dice
  const [currentRoll, setCurrentRoll] = useState<{ d1: number; d2: number } | null>(null);
  const [isRolling, setIsRolling] = useState(false);
  function onServerRolled(d1: number, d2: number) { setCurrentRoll({ d1, d2 }); setIsRolling(false); }

  // Dev hooks
  if (typeof window !== "undefined") {
    (window as any).simRoll = (d1: number, d2: number) => onServerRolled(d1, d2);
  }

  // Actions
  function handleRollDice() { setIsRolling(true);
    
     /* send WS action if needed */ }
  function handleTrade() { /* send WS action if needed */ }
  function handleBuyDev() { /* send WS action if needed */ }

  const devGroups = useMemo(() => {
    const counts = new Map<string, number>();
    self.devList.forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
    return Array.from(counts.entries()).map(([type, count]) => ({ type, count }));
  }, [self.devList]);

  // WebSocket
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    const url =
      (import.meta as any).env?.VITE_WS_URL ??
      `ws://localhost:8000/ws/1/1`; // ws://.../ws/{game_id}/{player_id}

    // Infer player id from URL if not set
    if (!selfId) {
      try {
        const pid = new URL(url).pathname.split("/").filter(Boolean).pop();
        if (pid) setSelfId(pid);
      } catch {}
    }

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => { /* optionally identify / subscribe */ };

      ws.onmessage = (ev) => {
        let data: any;
        try { data = JSON.parse(ev.data); } catch { data = ev.data; }

        // Detect controlling player from the snapshot (prefers entry with private info)
        const detected = (data && data.players) ? detectSelfFromSnapshot(data, selfId) : null;

        // Fallback chain if not a snapshot or nothing detected
        const candidateSelf =
          (detected ??
           data?.self_player_id ??
           data?.you_are ??
           selfId ??
           (() => {
             try {
               const pid = wsRef.current ? new URL(wsRef.current.url).pathname.split("/").filter(Boolean).pop() : null;
               return pid || null;
             } catch { return null; }
           })() ??
           "1");

        setSelfId(String(candidateSelf));

        // Full snapshot
        if (data?.board && data?.players) {
          const { overlay, players, bank } = toOverlayFromServer(data);
          setOverlay(overlay);
          setPlayers(players);
          setBank(bank);

          // Update self panel from snapshot using detected/candidate id
          const myId = String(candidateSelf);
          const sp = extractSelfPanel(data.players ?? {}, myId, PLAYER_COLORS);
          setSelf(sp);
        }

        // Dice event
        if (data?.type === "roll" && typeof data?.d1 === "number" && typeof data?.d2 === "number") {
          onServerRolled(data.d1, data.d2);
        }
      };

      ws.onerror = () => { /* optional toast/log */ };
      ws.onclose = () => { /* optional reconnect */ };

      return () => { ws.close(); };
    } catch {
      // ignore if environment blocks WS
    }
  }, [selfId]);

  // Dev helper: manual snapshot injection that also updates self
  useEffect(() => {
    if (typeof window === "undefined") return;
    (window as any).applyServer = (snap: any, me?: string | number) => {
      const { overlay, players, bank } = toOverlayFromServer(snap);
      setOverlay(overlay);
      setPlayers(players);
      setBank(bank);

      // Prefer auto-detect from snapshot; allow override via 2nd arg
      const auto = detectSelfFromSnapshot(snap, selfId);
      const myId = (me != null ? String(me) : auto);
      setSelfId(String(myId));
      const sp = extractSelfPanel(snap.players ?? {}, String(myId), PLAYER_COLORS);
      setSelf(sp);
    };
    (window as any).setSelfId = (pid: string) => setSelfId(String(pid));
  }, [selfId]);

  return (
    <div className="layout">
      {/* Main board area */}
      <div className="board">
        {/* LEFT HUD */}
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

          {/* YOU panel */}
          <div className="hud-card" style={{ borderLeft: `6px solid ${self.color}` }}>
            <h3 className="hud-title">You — {self.name}</h3>
            <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 6 }}>
              <div className="dot" style={{ background: self.color }} />
              <div>Victory Points: <strong>{self.victoryPoints}</strong></div>
              <div>VP Cards: <strong>{self.vpCards}</strong></div>
            </div>
          </div>

          {/* Development Cards (playable) */}
          <div className="dev-row">
            {self.devList.length > 0 ? (
              Object.entries(
                self.devList.reduce((acc: Record<string, number>, name) => {
                  acc[name] = (acc[name] ?? 0) + 1;
                  return acc;
                }, {})
              ).map(([type, count]) => (
                <div key={type} className="dev-card" title={`${type} ×${count}`}>
                  <span className="dev-emoji">
                    {type === "Knight" ? "⚔️" :
                     type === "Road Building" ? "🛣️" :
                     type === "Year of Plenty" ? "🎁" :
                     type === "Monopoly" ? "🎩" : "🎴"}
                  </span>
                  {count > 1 && <span className="dev-badge">{count}</span>}
                </div>
              ))
            ) : (
              <div style={{ opacity: .7 }}>No playable dev cards</div>
            )}
          </div>

          {/* Resources (your hand) */}
          <div className="hud-card">
            <h3 className="hud-title">Your Hand</h3>
            <div className="resource-grid">
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🌲</span></div><div className="count-pill">{self.resources.wood}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🧱</span></div><div className="count-pill">{self.resources.brick}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🐑</span></div><div className="count-pill">{self.resources.sheep}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">🌾</span></div><div className="count-pill">{self.resources.wheat}</div></div>
              <div className="resource-card"><div className="resource-left"><span className="resource-emoji">⛰️</span></div><div className="count-pill">{self.resources.ore}</div></div>
            </div>
          </div>
        </div>

        {/* The actual board, driven by live overlay */}
        <HexBoard overlay={overlay} />
      </div>

      {/* Right sidebar: Bank + Players */}
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
          <div className="card" key={p.id} style={p.isCurrent ? { outline: `6px solid ${p.color}` } : undefined}>
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
