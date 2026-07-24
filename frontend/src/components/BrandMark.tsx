interface BrandSymbolProps {
  size?: number;
  className?: string;
}

const NODES: [number, number][] = [
  [30, 8],
  [10, 22],
  [4, 44],
  [10, 66],
  [30, 80],
  [30, 44],
];

// Símbolo da marca (Seção 23.1/23.7 do PRD): rede de 6 nós conectados formando
// a letra "B", em gradiente linear azul profundo -> verde. SVG replicado
// ponto a ponto do protótipo de referência (função Logo()) para fidelidade
// visual exata — mesmo path, mesma posição dos nós, mesmo gradiente.
export function BrandSymbol({ size = 34, className }: BrandSymbolProps) {
  return (
    <svg width={size} height={(size * 88) / 60} viewBox="0 0 60 88" className={className} role="img" aria-label="Behavior Hub">
      <defs>
        <linearGradient id="bhSymbolGradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#1D4ED8" />
          <stop offset="100%" stopColor="#22C55E" />
        </linearGradient>
      </defs>
      <g stroke="url(#bhSymbolGradient)" strokeWidth={3} fill="none">
        <path d="M30 44 L30 8 L38 8 Q54 8 54 26 Q54 44 38 44" />
        <path d="M30 44 Q54 44 54 62 Q54 80 38 80 L30 80 L30 44" />
        {NODES.map(([x, y], i) => (
          <line key={i} x1="30" y1="44" x2={x} y2={y} />
        ))}
      </g>
      {NODES.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="5.5" fill="url(#bhSymbolGradient)" />
      ))}
      <circle cx="30" cy="44" r="7" fill="url(#bhSymbolGradient)" />
    </svg>
  );
}

interface LogoProps {
  compact?: boolean;
  dark?: boolean;
  className?: string;
}

// Logo completa (símbolo + wordmark), usada na sidebar (compact) e no login
// (tamanho grande). Réplica do componente Logo() do protótipo de referência.
export function Logo({ compact, dark, className }: LogoProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className ?? ""}`}>
      <BrandSymbol size={compact ? 26 : 34} />
      {!compact && (
        <div className="leading-none">
          <div className={`font-extrabold text-[17px] ${dark ? "text-brand-navy" : "text-white"}`}>Behavior</div>
          <div className="font-extrabold text-[17px] text-brand-turquoise">Hub</div>
        </div>
      )}
    </div>
  );
}

interface BrandLogoVerticalProps {
  className?: string;
  showTagline?: boolean;
}

// Logotipo vertical (Seção 23.2/23.8 do PRD): símbolo grande sobre a wordmark,
// usado na tela de login centralizado acima dos campos de formulário.
export function BrandLogoVertical({ className, showTagline = true }: BrandLogoVerticalProps) {
  return (
    <div className={`flex flex-col items-center gap-3 ${className ?? ""}`}>
      <BrandSymbol size={72} />
      <div className="text-2xl font-extrabold leading-none text-center">
        <span className="text-brand-navy">Behavior</span>
        <span className="text-brand-turquoise"> Hub</span>
      </div>
      {showTagline && (
        <p className="text-[10.5px] uppercase tracking-wide text-neutralState font-bold">
          Dados · Comportamento · Inteligência
        </p>
      )}
    </div>
  );
}
