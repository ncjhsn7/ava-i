import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService, Cadeira, Progresso } from '../services/api.service';
import { corCadeira, inicial } from '../cores';

@Component({
  selector: 'app-home',
  imports: [RouterLink],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css'
})
export class HomeComponent implements OnInit {
  api = inject(ApiService);

  cadeiras = signal<Cadeira[]>([]);
  qtdPdfs = signal<Record<number, number>>({});
  carregado = signal(false);
  erroApi = signal(false);

  cor = corCadeira;
  inicial = inicial;

  prog = signal<Progresso | null>(null);
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

  carregarProgresso() {
    this.api.progresso().subscribe({ next: p => this.prog.set(p), error: () => {} });
  }

  mudarMeta(ev: Event) {
    const meta = Number((ev.target as HTMLSelectElement).value);
    this.api.definirMeta(meta).subscribe(() => this.carregarProgresso());
  }

  nomeCadeira(id: number) {
    return this.cadeiras().find(c => c.id === id)?.nome ?? '';
  }

  ngOnInit() {
    this.carregarProgresso();
    this.api.listarCadeiras().subscribe({
      next: cs => {
        this.cadeiras.set(cs);
        this.carregado.set(true);
        if (!cs.length) return;
        forkJoin(cs.map(c => this.api.listarMateriais(c.id).pipe(catchError(() => of([])))))
          .subscribe(listas => {
            const mapa: Record<number, number> = {};
            cs.forEach((c, i) => (mapa[c.id] = listas[i].length));
            this.qtdPdfs.set(mapa);
          });
      },
      error: () => { this.carregado.set(true); this.erroApi.set(true); }
    });
  }

  rotuloPdfs(id: number) {
    const n = this.qtdPdfs()[id];
    if (n === undefined) return '';
    return n === 0 ? 'Nenhum PDF' : n === 1 ? '1 PDF' : `${n} PDFs`;
  }
}
