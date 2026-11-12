/** Schematic Caspian corridor map — not for navigation. */
export function CaspianMap({ selected = "SCT-2048" }: { selected?: string }) {
  return (
    <div className="caspian-map" aria-label="Схема Каспийского коридора">
      <svg viewBox="0 0 696 280" role="img">
        <ellipse cx="330" cy="150" rx="120" ry="95" fill="#c5dbe3" opacity="0.9" />
        <path
          d="M250 40 C 220 90, 230 160, 255 230 C 290 255, 360 250, 400 210 C 430 160, 420 80, 380 45 C 340 25, 280 20, 250 40 Z"
          fill="#b7d0db"
          stroke="#8fb0bf"
          strokeWidth="1"
        />
        <text x="50" y="48" fill="#687585" fontSize="11" fontFamily="Inter,sans-serif">
          РОССИЯ
        </text>
        <text x="492" y="48" fill="#687585" fontSize="11" fontFamily="Inter,sans-serif">
          КАЗАХСТАН
        </text>
        <text x="460" y="250" fill="#687585" fontSize="11" fontFamily="Inter,sans-serif">
          ИРАН
        </text>
        <text x="300" y="150" fill="#687585" fontSize="11" fontFamily="Inter,sans-serif" textAnchor="middle">
          КАСПИЙСКОЕ
        </text>
        <text x="300" y="166" fill="#687585" fontSize="11" fontFamily="Inter,sans-serif" textAnchor="middle">
          МОРЕ
        </text>
        <circle cx="270" cy="55" r="5" fill="#087f83" />
        <text x="165" y="42" fill="#17212b" fontSize="14" fontFamily="Inter,sans-serif" fontWeight="500">
          Астрахань
        </text>
        <circle cx="255" cy="145" r="4" fill="#687585" />
        <text x="150" y="148" fill="#687585" fontSize="13" fontFamily="Inter,sans-serif">
          Махачкала
        </text>
        <circle cx="415" cy="110" r="4" fill="#687585" />
        <text x="430" y="114" fill="#687585" fontSize="13" fontFamily="Inter,sans-serif">
          Актау
        </text>
        <circle cx="250" cy="205" r="4" fill="#687585" />
        <text x="180" y="210" fill="#687585" fontSize="13" fontFamily="Inter,sans-serif">
          Баку
        </text>
        <circle cx="340" cy="240" r="5" fill="#087f83" />
        <text x="355" y="245" fill="#17212b" fontSize="14" fontFamily="Inter,sans-serif" fontWeight="500">
          Энзели
        </text>
        <path
          d="M270 55 C 280 120, 310 180, 340 240"
          fill="none"
          stroke="#087f83"
          strokeWidth="2.5"
          strokeDasharray="6 6"
        />
      </svg>
      <span className="visually-hidden">{selected}</span>
    </div>
  );
}
