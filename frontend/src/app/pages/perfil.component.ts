import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, Cadeira, Progresso } from '../services/api.service';

@Component({
  selector: 'app-perfil',
  imports: [RouterLink],
  templateUrl: './perfil.component.html',
  styleUrl: './perfil.component.css'
})
export class PerfilComponent implements OnInit {
  api = inject(ApiService);

  cadeiras = signal<Cadeira[]>([]);
  prog = signal<Progresso | null>(null);
  erroApi = signal(false);

  metas = [5, 10, 15, 20, 30];
  pctNivel = computed(() => {
    const p = this.prog();
    if (!p) return 0;
    return Math.round(100 * (p.xp - p.xp_nivel_inicio) / (p.xp_proximo_nivel - p.xp_nivel_inicio));
  });
  pctMeta = computed(() => {
    const p = this.prog();
    return p ? Math.min(100, Math.round(100 * p.respondidas_hoje / p.meta_diaria)) : 0;
  });
  circMeta = 2 * Math.PI * 26;

  ngOnInit() {
    this.carregarProgresso();
    this.api.listarCadeiras().subscribe({ next: cs => this.cadeiras.set(cs), error: () => {} });
  }

  carregarProgresso() {
    this.api.progresso().subscribe({ next: p => this.prog.set(p), error: () => this.erroApi.set(true) });
  }

  mudarMeta(ev: Event) {
    const meta = Number((ev.target as HTMLSelectElement).value);
    this.api.definirMeta(meta).subscribe(() => this.carregarProgresso());
  }

  /** Compara sem acento/maiúsculas: "Inteligencia Artificial" == "Inteligência Artificial". */
  mesmoNome(a: string, b: string) {
    const n = (s: string) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();
    return n(a) === n(b);
  }

  nomeCadeira(id: number) {
    return this.cadeiras().find(c => c.id === id)?.nome ?? '';
  }
}
