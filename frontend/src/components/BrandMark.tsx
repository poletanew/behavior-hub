interface BrandSymbolProps {
  size?: number;
  className?: string;
}

// Símbolo reduzido da marca (Seção 23.1/23.7 do PRD): rede de nós conectados
// formando a letra "B", em gradiente azul -> turquesa -> verde.
export function BrandSymbol({ size = 40, className }: BrandSymbolProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label="Behavior Hub"
    >
      <defs>
        <linearGradient id="bhSymbolGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1D4ED8" />
          <stop offset="55%" stopColor="#14B8A6" />
          <stop offset="100%" stopColor="#22C55E" />
        </linearGradient>
      </defs>
      <path
        d="M20 15 L20 49 M20 15 C34 15 40 19 40 24 C40 29 34 32 20 32 M20 32 C36 32 43 36 43 41 C43 46 36 49 20 49"
        fill="none"
        stroke="url(#bhSymbolGradient)"
        strokeWidth={6.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="20" cy="15" r="4" fill="#1D4ED8" />
      <circle cx="20" cy="32" r="4" fill="#14B8A6" />
      <circle cx="20" cy="49" r="4" fill="#22C55E" />
      <circle cx="40" cy="24" r="3.2" fill="#1D4ED8" />
      <circle cx="43" cy="41" r="3.2" fill="#22C55E" />
    </svg>
  );
}

interface BrandLogoVerticalProps {
  className?: string;
  showTagline?: boolean;
}

// Logotipo vertical (Seção 23.2/23.8 do PRD): símbolo sobre a wordmark,
// usado na tela de login centralizado acima dos campos de formulário.
export function BrandLogoVertical({ className, showTagline = true }: BrandLogoVerticalProps) {
  return (
    <div className={`flex flex-col items-center gap-2 ${className ?? ""}`}>
      <BrandSymbol size={56} />
      <div className="text-2xl font-extrabold leading-none">
        <span className="text-brand-navy">Behavior</span> <span className="text-brand-turquoise">Hub</span>
      </div>
      {showTagline && (
        <p className="text-[11px] uppercase tracking-wide text-neutralState">
          Dados. Comportamento. Inteligência.
        </p>
      )}
    </div>
  );
}
