export const SPECIALTIES = [
  { value: "psicologo_infantil", label: "Psicólogo infantil" },
  { value: "analista_comportamento_aba", label: "Analista do Comportamento / ABA" },
  { value: "fonoaudiologo", label: "Fonoaudiólogo" },
  { value: "terapeuta_ocupacional", label: "Terapeuta Ocupacional" },
  { value: "psicopedagogo", label: "Psicopedagogo" },
  { value: "fisioterapeuta_pediatrico", label: "Fisioterapeuta pediátrico" },
  { value: "neuropediatra", label: "Neuropediatra" },
  { value: "psiquiatra_infantil", label: "Psiquiatra infantil" },
  { value: "nutricionista_infantil", label: "Nutricionista infantil" },
  { value: "musicoterapeuta", label: "Musicoterapeuta" },
  { value: "arteterapeuta", label: "Arteterapeuta" },
  { value: "psicomotricista", label: "Psicomotricista" },
];

const SPECIALTY_LABELS: Record<string, string> = Object.fromEntries(
  SPECIALTIES.map((s) => [s.value, s.label]),
);

// RF-07 do Addendum v2.1: o profissional responsável é exibido com a
// especialidade ao lado do nome (ex.: "Ana Ribeiro — Psicóloga infantil").
export function specialtyLabel(specialty: string | null | undefined): string | null {
  if (!specialty) return null;
  return SPECIALTY_LABELS[specialty] ?? specialty;
}

export function professionalDisplayName(person: { name: string; specialty?: string | null }): string {
  const label = specialtyLabel(person.specialty);
  return label ? `${person.name} — ${label}` : person.name;
}
