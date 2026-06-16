import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, Cadeira, Painel } from '../services/api.service';

@Component({
  selector: 'app-painel',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Painel</div>
        <h2>Desempenho por cadeira</h2>
        <p>Acompanhe quantas sessões aconteceram, o índice de acerto e onde os alunos têm mais dificuldade.</p>
      </div>

      @if (!cadeiraId()) {
        @if (cadeiras().length === 0) {
          <p class="vazio">Nenhuma cadeira ainda.</p>
        } @else {
          <div class="grade">
            @for (c of cadeiras(); track c.id) {
              <button class="curso" (click)="selecionar(c.id)">
                <div class="banner" [style.background]="corCadeira(c.id)"><span>{{ inicial(c.nome) }}</span></div>
                <div class="curso-nome">{{ c.nome }}</div>
              </button>
            }
          </div>
        }
      } @else {
        <button class="voltar" (click)="selecionar(0)">← Todas as cadeiras</button>
        <h3 class="titulo-cadeira">{{ nomeCadeira() }}</h3>

        @if (dados()) {
          <div class="kpis">
            <div class="kpi"><b>{{ dados()!.kpis.sessoes }}</b><span>Sessões</span></div>
            <div class="kpi"><b>{{ dados()!.kpis.respostas }}</b><span>Respostas</span></div>
            <div class="kpi"><b>{{ dados()!.kpis.acerto_medio }}%</b><span>Acerto médio</span></div>
            <div class="kpi"><b>{{ dados()!.kpis.foco_medio ?? '—' }}</b><span>Foco médio</span></div>
          </div>

          @if (dados()!.acertos_por_topico.length) {
            <div class="cartao">
              <div class="titulo-bloco">Acerto por tópico</div>
              @for (b of dados()!.acertos_por_topico; track b.topico) {
                <div class="barra-linha">
                  <span class="rotulo">{{ b.topico }}</span>
                  <div class="barra"><div class="preenche" [style.width.%]="b.acerto ?? 0"></div></div>
                  <span class="valor">{{ b.acerto ?? '—' }}{{ b.acerto !== null ? '%' : '' }} <small>({{ b.respostas }})</small></span>
                </div>
              }
            </div>
          } @else {
            <p class="vazio">Ainda não há respostas registradas nesta cadeira.</p>
          }
        } @else {
          <p class="vazio">Carregando…</p>
        }
      }
    </div>
  `,
  styles: `
    .grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}
    .curso{text-align:left;background:var(--surface);border:1px solid var(--linha);border-radius:4px;overflow:hidden;padding:0;transition:border-color .15s,transform .15s}
    .curso:hover{border-color:var(--accent);transform:translateY(-2px)}
    .banner{height:92px;display:flex;align-items:center;justify-content:center}
    .banner span{font-size:32px;font-weight:700;color:rgba(255,255,255,.92)}
    .curso-nome{padding:13px 15px;font-weight:600;font-size:14px}
    .voltar{color:var(--ink-soft);font-weight:600;font-size:13px}
    .voltar:hover{color:var(--ink)}
    .titulo-cadeira{margin:14px 0 6px;font-size:18px}
    .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
    .kpi{background:var(--surface);border:1px solid var(--linha);border-radius:4px;padding:18px;text-align:center}
    .kpi b{font-size:28px;display:block;color:var(--accent)}
    .kpi span{font-size:12px;color:var(--ink-soft);text-transform:uppercase;letter-spacing:.05em}
    .titulo-bloco{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-soft);margin-bottom:14px}
    .barra-linha{display:grid;grid-template-columns:1fr 2fr auto;gap:12px;align-items:center;margin-bottom:10px}
    .rotulo{font-size:13px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .barra{height:10px;background:var(--surface-2);border-radius:3px;overflow:hidden}
    .preenche{height:100%;background:var(--accent);border-radius:3px;transition:width .5s}
    .valor{font-size:13px;color:var(--ink-soft);font-family:var(--mono)}
    .valor small{opacity:.6}
    @media(max-width:680px){.kpis{grid-template-columns:repeat(2,1fr)}}
  `
})
export class PainelComponent implements OnInit {
  api = inject(ApiService);

  cadeiras = signal<Cadeira[]>([]);
  cadeiraId = signal(0);
  dados = signal<Painel | null>(null);

  ngOnInit() {
    this.api.listarCadeiras().subscribe(cs => this.cadeiras.set(cs));
  }

  inicial(nome: string) {
    return (nome.trim().charAt(0) || '?').toUpperCase();
  }

  corCadeira(id: number) {
    const h = (id * 47) % 360;
    return `hsl(${h},38%,38%)`;
  }

  nomeCadeira() {
    return this.cadeiras().find(c => c.id === this.cadeiraId())?.nome ?? '';
  }

  selecionar(id: number) {
    this.cadeiraId.set(id);
    this.dados.set(null);
    if (id) this.api.painel(id).subscribe(d => this.dados.set(d));
  }
}
