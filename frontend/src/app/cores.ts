// Paleta de cores sólidas das cadeiras (tons de marca-texto).
const PALETA = ['#ffd43b', '#ff8fab', '#69db7c', '#74c0fc', '#ffa94d', '#b197fc', '#63e6be', '#ff6b6b'];

export function corCadeira(id: number): string {
  return PALETA[Math.abs(id - 1) % PALETA.length];
}

export function inicial(nome: string): string {
  return (nome.trim().charAt(0) || '?').toUpperCase();
}
