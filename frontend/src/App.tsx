import { useState, useMemo } from "react";
import { useEffect } from "react";
import {
  Trophy, Swords, Route, Building, Home, Hand, Minus, Layers,
  Dice5, ShoppingBag, Handshake
} from "lucide-react";
import "./App.css";
import HexBoard from "./Board";

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
};

type Bank = {
  wood: number;
  brick: number;
  sheep: number;
  wheat: number;
  ore: number;
  devCards: number;
};






export default function App() {
  const [players] = useState<Player[]>([
    { id: "1", name: "Player 1", color: "#ef4444", victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "2", name: "Player 2", color: "#3b82f6", victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "3", name: "Player 3", color: "#22c55e", victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
    { id: "4", name: "Player 4", color: "#f59e0b", victoryPoints: 0, largestArmy: 0, longestRoad: 0, cities: 0, settlements: 0, roads: 0, handSize: 0, devCards: 0 },
  ]);

  const [bank] = useState<Bank>({
    wood: 19, brick: 19, sheep: 19, wheat: 19, ore: 19, devCards: 25,
  });

  const DEV_EMOJI: Record<string, string> = {
    "Knight": "⚔️",
    "Road Building": "🛣️",
    "Year of Plenty": "🎁",
    "Monopoly": "🎩",
  };

  const DIE = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];

  const [currentRoll, setCurrentRoll] = useState<{ d1: number; d2: number } | null>(null);
  const [isRolling, setIsRolling] = useState(false);

  function onServerRolled(d1: number, d2: number) {
    setCurrentRoll({ d1, d2 });
    setIsRolling(false);
  }

  if (typeof window !== "undefined") {
    (window as any).s = (d1: number, d2: number) => onServerRolled(d1, d2);
    (window as any).sr = () => {
      const d1 = 1 + Math.floor(Math.random() * 6);
      const d2 = 1 + Math.floor(Math.random() * 6);
      onServerRolled(d1, d2);
    };
  }

  // --- Your hand (example data; wire to websocket later) ---
  const [playableDevCards, setPlayableDevCards] = useState<string[]>([
    "Knight", "Knight", "Knight", "Road Building", "Year of Plenty", "Monopoly",
  ]);
  const [vpCards, setVpCards] = useState<number>(1);
  const [resources, setResources] = useState<{ wood: number; brick: number; sheep: number; wheat: number; ore: number; }>(
    { wood: 2, brick: 1, sheep: 3, wheat: 0, ore: 2 }
  );

  function handleRollDice() {
    setIsRolling(true);
    console.log("Roll dice clicked");
    // TODO: send over websocket
  }
  function handleTrade() {
    console.log("Open trade popup");
    // TODO: open modal / emit event
  }
  function handleBuyDev() {
    console.log("Buy development card");
    // TODO: send buy request
  }
  function playDev(type: string) {
    console.log("Play dev card:", type);
    setPlayableDevCards(prev => {
      const i = prev.indexOf(type);
      if (i === -1) return prev;
      const next = prev.slice();
      next.splice(i, 1);   // remove one instance
      return next;
    });
    // TODO: emit websocket action
  }


  const devGroups = useMemo(() => {
    const counts = new Map<string, number>();
    playableDevCards.forEach((c) => counts.set(c, (counts.get(c) ?? 0) + 1));
    return Array.from(counts.entries()).map(([type, count]) => ({ type, count }));
  }, [playableDevCards]);

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
                onClick={() => playDev(type)}        // plays one copy
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

          {/* Resources */}
          <div className="hud-card">
            <h3 className="hud-title">Resources</h3>
            <div className="resource-grid">
              <div className="resource-card">
                <div className="resource-left"><span className="resource-emoji">🌲</span> </div>
                <div className="count-pill">{resources.wood}</div>
              </div>
              <div className="resource-card">
                <div className="resource-left"><span className="resource-emoji">🧱</span> </div>
                <div className="count-pill">{resources.brick}</div>
              </div>
              <div className="resource-card">
                <div className="resource-left"><span className="resource-emoji">🐑</span> </div>
                <div className="count-pill">{resources.sheep}</div>
              </div>
              <div className="resource-card">
                <div className="resource-left"><span className="resource-emoji">🌾</span> </div>
                <div className="count-pill">{resources.wheat}</div>
              </div>
              <div className="resource-card">
                <div className="resource-left"><span className="resource-emoji">⛰️</span> </div>
                <div className="count-pill">{resources.ore}</div>
              </div>
            </div>
          </div>
        </div>

        {/* The board SVG sits underneath the HUD */}
        <HexBoard />
      </div>

      {/* Right: existing sidebar (Bank + Players) */}
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
          <div className="card" key={p.id}>
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
          </div>
        ))}
      </aside>
    </div>
  );
}
