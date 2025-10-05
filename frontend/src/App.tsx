// App.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Trophy, Swords, Route, Hand, Layers,
  Dice5, ShoppingBag, Handshake, Bot, UserPlus, UserMinus, Play, KeyRound, Users
} from "lucide-react";
import "./App.css";
import HexBoard from "./Board";
import type { BoardOverlay, ClickEdgePayload, ClickVertexPayload } from "./Board";

/** ================== Types ================== */
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
  current_roll: number | null;
};

type SelfPanel = {
  id: string;
  name: string;
  color: string;
  victoryPoints: number;
  resources: { wood: number; brick: number; sheep: number; wheat: number; ore: number };
  devList: string[];
  vpCards: number;
};

type Phase = "lobby" | "game";

/** ================== Constants ================== */
const API_URL = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = (import.meta as any).env?.VITE_WS_URL_BASE ?? "ws://localhost:8000"; // we append /ws/{gid}/{pid}

const PLAYER_COLORS: Record<string, string> = {
  1: "#f97316",
  2: "#a855f7",
  3: "#003049",
  4: "#780000",
};
const DIE = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];

/** ================== Helpers for server snapshots ================== */
function parseMaybeJSONString<T = any>(v: any): T {
  if (typeof v === "string") {
    try { return JSON.parse(v) as T; } catch { return v as T; }
  }
  return v as T;
}

function looksLikeSelfEntry(raw: any): boolean {
  if (!raw || typeof raw !== "object") return false;
  const hasHandObj = !!(raw.resources || raw.hand);
  const hasFlatResourceCounts =
    ["wood", "brick", "sheep", "wheat", "ore", "Wood", "Brick", "Sheep", "Wheat", "Ore"]
      .some(k => typeof (raw as any)[k] === "number");
  const hasDevList = Array.isArray((raw as any).development_cards) || Array.isArray((raw as any).dev_cards);
  const hasDevCounts = !!((raw as any).development_cards_counts || (raw as any).dev_cards_counts);
  return !!(hasHandObj || hasFlatResourceCounts || hasDevList || hasDevCounts);
}

function normalizeResources(raw: any): SelfPanel["resources"] {
  const src = raw?.resources ?? raw?.hand ?? raw ?? {};
  const n = (v: any) => (typeof v === "number" ? v : 0);
  return {
    wood: n(src.wood ?? src.Wood),
    brick: n(src.brick ?? src.Brick),
    sheep: n(src.sheep ?? src.Sheep),
    wheat: n(src.wheat ?? src.Wheat),
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
    const pushTimes = (label: string, times: number | undefined) => { for (let i = 0; i < (times || 0); i++) out.push(label); };
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

function detectSelfFromSnapshot(server: any, fallback: string | null): string {
  const playersMap = server?.players ?? {};
  for (const [pid, entry] of Object.entries(playersMap)) {
    const raw = parseMaybeJSONString(entry);
    if (looksLikeSelfEntry(raw)) return String(pid);
  }
  const hinted = server?.self_player_id ?? server?.you_are ?? null;
  if (hinted != null) return String(hinted);
  return String(fallback ?? "1");
}

function computeHighlightId(server: any): string | null {
  const placementRaw =
    server?.initial_placement_order ??
    server?.inital_placement_order ?? null;
  if (placementRaw !== null && placementRaw !== undefined && Number(placementRaw) !== -1) {
    return String(placementRaw);
  }
  if (server?.current_turn !== null && server?.current_turn !== undefined) {
    return String(server.current_turn);
  }
  return null;
}

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
    current_roll: server?.current_roll ?? null,
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

``

/** ================== Component ================== */
export default function App() {
  /** ----- Phase & Lobby state ----- */
  const [phase, setPhase] = useState<Phase>("lobby");
  const [gameId, setGameId] = useState<number | null>(null);
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [joinCode, setJoinCode] = useState<string>("");

  // Observed players in lobby (server only sends join/leave events pre-start)
  const [observedPlayers, setObservedPlayers] = useState<Set<number>>(new Set());

  /** ----- Game state (existing HUD/board bits) ----- */
  const [players, setPlayers] = useState<Player[]>([
    { id: "1", name: "Player 1", color: PLAYER_COLORS["1"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "2", name: "Player 2", color: PLAYER_COLORS["2"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "3", name: "Player 3", color: PLAYER_COLORS["3"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "4", name: "Player 4", color: PLAYER_COLORS["4"], victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
  ]);
  const [bank, setBank] = useState<Bank>({ wood: 19, brick: 19, sheep: 19, wheat: 19, ore: 19, devCards: 25, current_roll: null });
  const [overlay, setOverlay] = useState<BoardOverlay>({ tiles: [], edges: [], vertices: [] });

  // Self panel
  const [self, setSelf] = useState<SelfPanel>({
    id: "1",
    name: `Player 1`,
    color: PLAYER_COLORS["1"] ?? "#94a3b8",
    victoryPoints: 0,
    resources: { wood: 0, brick: 0, sheep: 0, wheat: 0, ore: 0 },
    devList: [],
    vpCards: 0,
  });

  const isMyTurn = players.find(p => p.id === self.id)?.isCurrent ?? false;

  const canEndTurn = useMemo(() => {
    const hasRolled = bank.current_roll !== null;
    return isMyTurn && hasRolled;
  }, [players, self.id, bank.current_roll]);

  // NEW: what the board says is currently selected
  const [selected, setSelected] = useState<{ type: 'tile' | 'edge' | 'vertex'; id: number } | null>(null);

  // NEW: compute the context-aware action label + enabled flag
  const buildAction = useMemo(() => {
    if (!selected) return { label: "Select a tile/edge/node", enabled: false };
    if (selected.type === "tile") {
      return { label: "Place Robber", enabled: true }; // wrapper only (TODO)
    }
    if (selected.type === "edge") {
      const e = overlay.edges?.[selected.id];
      const taken = e?.owner != null;
      return taken
        ? { label: "Edge occupied", enabled: false }
        : { label: "Build Road", enabled: true };
    }
    // vertex
    const v = overlay.vertices?.[selected.id];
    const b = (v?.building || "").toString().toLowerCase();
    if (b === "settlement") return { label: "Build City", enabled: true };
    if (!b) return { label: "Build Settlement", enabled: true };
    return { label: "Vertex occupied", enabled: false };
  }, [selected, overlay]);



  function handleEndTurn() { sendAction({ type: "end_turn" }); }
  function handleBuyDev() { sendAction({ type: "buy_development_card" }); }

  // Actions (hook up to WS later if you have action routing)
  function handleRollDice() { sendAction({ type: "roll_dice" }); }
  function handleTrade() { /* send WS action if needed */ }


  // NEW: click handler (wrapper only for now)
  function handleBuildClick() {
    if (!buildAction.enabled || !selected) return;

    // Edges → place_road
    if (selected.type === "edge") {
      sendAction({ type: "place_road", edge_id: selected.id });
      return;
    }

    // Vertices → place_settlement or place_city (if it's your settlement)
    if (selected.type === "vertex") {
      const v = overlay.vertices?.[selected.id];
      const building = (v?.building || "").toString().toLowerCase();
      const ownerStr = v?.owner != null ? String(v.owner) : null;

      // Empty vertex → settlement
      if (!building) {
        sendAction({ type: "place_settlement", vertex_id: selected.id });
        return;
      }
      // Your settlement → upgrade to city
      if (building === "settlement" && ownerStr === self.id) {
        sendAction({ type: "place_city", vertex_id: selected.id });
        return;
      }
    }

    // Tiles are ignored here (robber wrapper/TODO).
  }

  /** ----- WebSocket (shared for lobby and game) ----- */
  const wsRef = useRef<WebSocket | null>(null);

  // Helper to send actions to the server over WS
  function sendAction(payload: Record<string, any>) {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { ws.send(JSON.stringify(payload)); } catch (e) { console.error("WS send failed", e); }
    } else {
      console.warn("WebSocket not connected; cannot send action", payload);
    }
  }

  // Connect WS when we know gameId & playerId
  useEffect(() => {
    if (!gameId || !playerId) return;
    // Close any existing
    if (wsRef.current) { try { wsRef.current.close(); } catch { } wsRef.current = null; }

    const ws = new WebSocket(`${WS_URL}/ws/${gameId}/${playerId}`); // ws://.../ws/{game_id}/{player_id}
    wsRef.current = ws;

    ws.onopen = () => {
      // Add self to observed list
      setObservedPlayers((prev) => new Set(prev).add(playerId));
    };


    ws.onmessage = (ev) => {
      let data: any;
      try { data = JSON.parse(ev.data); } catch { data = ev.data; }

      // --- NEW: full snapshot for late joiners ---
      if (data?.type === "lobby_state" && Array.isArray(data.players)) {
        setObservedPlayers(new Set<number>(data.players.map((n: number) => Number(n))));
        return;
      }

      // existing:
      if (data?.status === "player_joined" && typeof data.player_id === "number") {
        setObservedPlayers(prev => {
          const next = new Set(prev);
          next.add(data.player_id);
          return next;
        });
        return;
      }
      if (data?.status === "player_disconnected" && typeof data.player_id === "number") {
        setObservedPlayers(prev => {
          const next = new Set(prev);
          next.delete(data.player_id);
          return next;
        });
        return;
      }

      // --- LOBBY-ONLY events before game starts ---
      if (data?.status === "player_joined" && typeof data.player_id === "number") {
        setObservedPlayers((prev) => {
          const next = new Set(prev);
          next.add(data.player_id);
          return next;
        });
        return;
      }
      if (data?.status === "player_disconnected" && typeof data.player_id === "number") {
        setObservedPlayers((prev) => {
          const next = new Set(prev);
          next.delete(data.player_id);
          return next;
        });
        return;
      }
      if (data?.type === "ping") {
        // keep-alive during lobby; nothing to do
        return;
      }

      // --- GAME START SIGNALS ---
      // server sends {"game_state":"True"} to all when start called, followed by per-player snapshot
      if (data?.game_state === "True") {
        setPhase("game");
        return;
      }

      // --- FULL SNAPSHOT DURING GAME ---
      if (data?.board && data?.players) {
        setPhase("game");

        const { overlay, players, bank } = toOverlayFromServer(data);
        setOverlay(overlay);
        setPlayers(players);
        setBank(bank);

        // Detect controlling player ID from snapshot
        const detectedSelf = detectSelfFromSnapshot(data, String(playerId));
        const sp = extractSelfPanel(data.players ?? {}, String(detectedSelf), PLAYER_COLORS);
        setSelf(sp);
        return;
      }
    };

    ws.onclose = () => { /* optionally: setPhase("lobby") */ };
    ws.onerror = () => { /* optional log */ };

    return () => { try { ws.close(); } catch { } };
  }, [gameId, playerId]);

  /** ----- REST helpers (same endpoints as in board.html) ----- */
  async function createLobby() {
    // POST /create -> { game_id, player_id }
    const res = await fetch(`${API_URL}/create`, { method: "POST" });
    const data = await res.json();
    setGameId(data.game_id);
    setPlayerId(data.player_id);
    setObservedPlayers(new Set([data.player_id]));
  }

  async function joinLobby() {
    if (!joinCode.trim()) return;
    const code = parseInt(joinCode.trim(), 10);
    const res = await fetch(`${API_URL}/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_id: code }),
    });

    const data = await res.json();
    if (data.message) {
      alert(`Join failed: ${data.message}`);
      return;
    }
    setGameId(data.game_id);
    setPlayerId(data.player_id);
    setObservedPlayers(new Set([data.player_id]));
  }

  async function startGame() {
    if (!gameId) return;
    const res = await fetch(`${API_URL}/game/${gameId}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_id: gameId }),
    });
    const data = await res.json();
    if (data.message && /already started|Not enough/.test(data.message)) {
      alert(data.message);
    }
    // After this, server will push game_state + first snapshot via WS
  }

  async function addBot() {
    if (!gameId) return;
    const res = await fetch(`${API_URL}/game/${gameId}/add_bot`, { method: "POST" });
    if (!res.ok) alert("add_bot not implemented on server yet.");
  }

  async function removeBot() {
    if (!gameId) return;
    const res = await fetch(`${API_URL}/game/${gameId}/remove_bot`, { method: "POST" });
    if (!res.ok) alert("remove_bot not implemented on server yet.");
  }

  /** ----- Dev helper: manual snapshot injection that also updates self ----- */
  useEffect(() => {
    if (typeof window === "undefined") return;
    (window as any).applyServer = (snap: any, me?: string | number) => {
      const { overlay, players, bank } = toOverlayFromServer(snap);
      setOverlay(overlay);
      setPlayers(players);
      setBank(bank);

      const auto = detectSelfFromSnapshot(snap, self.id);
      const myId = (me != null ? String(me) : auto);
      const sp = extractSelfPanel(snap.players ?? {}, String(myId), PLAYER_COLORS);
      setSelf(sp);
      setPhase("game");
    };
  }, [self.id]);

  /** ================== UI ================== */
  if (phase === "lobby") {
    const count = observedPlayers.size;
    return (
      <div className="lobby-wrap" style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "linear-gradient(180deg,#0f172a,#1e293b)" }}>
        <div className="lobby-card" style={{ width: 520, background: "grey", borderRadius: 16, padding: 20, boxShadow: "0 10px 30px rgba(0,0,0,.25)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <KeyRound /> <h2 style={{ margin: 0 }}>Catan</h2>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <button onClick={createLobby} className="btn primary" style={{ padding: 12, borderRadius: 10 }}>
              <UserPlus size={18} /> Create new lobby
            </button>

            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                placeholder="Enter lobby code"
                className="input"
                style={{ flex: 1, padding: 10, borderRadius: 10, border: "1px solid #e2e8f0" }}
              />
              <button onClick={joinLobby} className="btn" style={{ padding: "10px 14px", borderRadius: 10 }}>
                Join
              </button>
            </div>

            <div style={{ display: "grid", gap: 8, marginTop: 6, background: "grey", padding: 12, borderRadius: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Users size={18} /> <strong>Players connected:</strong> {count}/4
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 6 }}>
                <button onClick={startGame} disabled={(count < 2) || !gameId} className="btn success" style={{ padding: 10, borderRadius: 10 }}>
                  <Play size={16} /> Start Game
                </button>
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={addBot} disabled={!gameId} className="btn" title="Add bot" style={{ padding: 10, borderRadius: 10 }}>
                    <Bot size={16} /> Add Bot
                  </button>
                  <button onClick={removeBot} disabled={!gameId} className="btn" title="Remove bot" style={{ padding: 10, borderRadius: 10 }}>
                    <UserMinus size={16} /> Remove Bot
                  </button>
                </div>
              </div>

              <div style={{ display: "grid", gap: 4, marginTop: 4, fontSize: 14 }}>
                <div>
                  <strong>Lobby code:</strong>{" "}
                  {gameId !== undefined && gameId !== null && String(gameId).trim() !== "" ? (
                    <span style={{ fontWeight: 800, fontSize: 20, letterSpacing: 0.5 }}>
                      {String(gameId)}
                    </span>
                  ) : (
                    <span>--</span>
                  )}
                </div>

                <div>
                  <strong>You are:</strong>{" "}
                  {playerId !== undefined && playerId !== null && String(playerId).trim() !== "" ? (
                    <span style={{ fontWeight: 700, fontSize: 18 }}>
                      {`Player ${playerId}`}
                    </span>
                  ) : (
                    <span>--</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ====== GAME PHASE (your existing HUD/board UI) ======
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
              <button
                onClick={handleRollDice}
                disabled={!isMyTurn || bank.current_roll !== null}
                title="Roll Dice"
                className="btn-accent hud-btn-primary"
                style={{ ["--accent" as any]: self.color }}
              >
                Roll
              </button>

              <button
                onClick={handleTrade}
                disabled={!canEndTurn}
                title="Trade"
                className="btn-accent"
                style={{ ["--accent" as any]: self.color }}
              >
                Trade
              </button>

              <button
                onClick={handleBuyDev}
                disabled={!canEndTurn}
                title="Buy Dev"
                className="btn-accent"
                style={{ ["--accent" as any]: self.color }}
              >
                Buy Dev
              </button>
            </div>



            <div className="roll-row">
              <span className="roll-label">Current roll</span>
              <span className="roll-pill">
                <span className="roll-dice">
                  {bank.current_roll ? bank.current_roll : "— —"}
                </span>
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

          {/* NEW: Single context-aware build button */}
          <div className="hud-card">
            <h3 className="hud-title">Build</h3>
            <div style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ opacity: selected ? 1 : 0.7 }}>
                {selected
                  ? (selected.type === "tile" && <>Tile <strong>#{selected.id}</strong></>) ||
                  (selected.type === "edge" && <>Edge <strong>#{selected.id}</strong></>) ||
                  (selected.type === "vertex" && <>Node <strong>#{selected.id}</strong></>)
                  : <>Nothing selected</>}
              </div>
              <button
                onClick={handleBuildClick}
                disabled={!buildAction.enabled}
                className="btn-accent"
                /* feed the player color into a CSS variable read by .btn-accent */
                style={{ ["--accent" as any]: self.color }}
              >
                {buildAction.label}
              </button>
            </div>
          </div>

          {/* NEW: End Turn button (under Build) */}
          <div className="hud-card">
            <button
              onClick={handleEndTurn}
              disabled={!canEndTurn}
              className="btn-accent"
              style={{ ["--accent" as any]: self.color, width: "100%" }}
            >
              End Turn
            </button>
          </div>

        </div>

        {/* The actual board, driven by live overlay */}
        <HexBoard overlay={overlay} onSelect={setSelected} />
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
              <div className="stat"><Hand /> <span>{p.handSize}</span></div>
              <div className="stat"><Route /> <span>{p.longestRoad}</span></div>
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