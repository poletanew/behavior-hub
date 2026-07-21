import { SchoolShift } from "../types";

const SCHOOL_SHIFT_LABELS: Record<SchoolShift, string> = {
  manha: "Manhã",
  tarde: "Tarde",
  integral: "Integral",
  nao_frequenta: "Não frequenta",
};

export function schoolShiftLabel(shift: SchoolShift | null | undefined): string | null {
  if (!shift) return null;
  return SCHOOL_SHIFT_LABELS[shift] ?? shift;
}

export function calculateAge(birthDate: string): number {
  const birth = new Date(birthDate);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const hasNotHadBirthdayThisYear =
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate());
  if (hasNotHadBirthdayThisYear) age -= 1;
  return age;
}

// Máscara simples de telefone brasileiro (RF-03): (11) 91234-5678 / (11) 1234-5678.
export function formatPhoneInput(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
