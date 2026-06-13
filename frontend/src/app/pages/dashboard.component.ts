import { Component, OnInit, inject, signal } from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { ApiService, DadosDashboard, Material } from '../services/api.service';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Módulo 3 · Dashboard analítico do docente</div>
        <h2>Engajamento × desempenho</h2>
        <p>Dados agregados e anonimizados das sessões registradas no backend.</p>
      </div>

      @if (materiais().length === 0) {
        <div class="cartao">Nenhum material com sessões ainda.</div>
      } @else {
        <label>Material
          <select [value]="materialId()" (change)="trocar(+$any($event.target).value)">
            @for (m of materiais(); track m.id) {
              <option [value]="m.id">{{ m.titulo }}</option>
            }
          </select>
        </label>

        @if (dados(); as d) {
          <div class="kpis">
            <div class="cartao kpi"><div class="rotulo">Sessões</div><b>{{ d.kpis.sessoes }}</b></div>
            <div class="cartao kpi"><div class="rotulo">focusScore médio</div><b>{{ d.kpis.focus_medio }}%</b></div>
            <div class="cartao kpi"><div class="rotulo">Eventos de celular · controle</div><b>{{ d.kpis.eventos_controle }}</b></div>
            <div class="cartao kpi"><div class="rotulo">Eventos de celular · intervenção</div><b>{{ d.kpis.eventos_intervencao }}</b></div>
          </div>
          <div class="graficos">
            <div class="cartao grafico">
              <h4>Engajamento ao longo da sessão (QP2)</h4>
              <canvas id="chartEngajamento"></canvas>
            </div>
            <div class="cartao grafico">
              <h4>Acerto por questão formativa</h4>
              <canvas id="chartAcertos"></canvas>
            </div>
            <div class="cartao grafico largo">
              <h4>focusScore × accuracyRate por sessão (QP1)</h4>
              <canvas id="chartPontos"></canvas>
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: `
    label{display:block;margin-bottom:18px;font-weight:600;font-size:13px}
    label select{display:block;margin-top:6px;min-width:320px}
    .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:20px}
    .kpi .rotulo{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-soft)}
    .kpi b{display:block;font-size:28px;margin-top:6px}
    .graficos{display:grid;grid-template-columns:1fr 1fr;gap:14px}
    .grafico h4{font-size:15px;margin-bottom:12px}
    .grafico canvas{max-height:240px}
    .largo{grid-column:1/-1}
    @media(max-width:920px){.graficos{grid-template-columns:1fr}}
  `
})
export class DashboardComponent implements OnInit {
  api = inject(ApiService);
  materiais = signal<Material[]>([]);
  materialId = signal(0);
  dados = signal<DadosDashboard | null>(null);
  private charts: Chart[] = [];

  ngOnInit() {
    this.api.listarMateriais().subscribe(ms => {
      this.materiais.set(ms);
      if (ms.length) this.trocar(ms[0].id);
    });
  }

  trocar(id: number) {
    this.materialId.set(id);
    this.api.dashboard(id).subscribe(d => {
      this.dados.set(d);
      setTimeout(() => this.desenhar(d));
    });
  }

  private desenhar(d: DadosDashboard) {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
    const eng = document.getElementById('chartEngajamento') as HTMLCanvasElement | null;
    const ace = document.getElementById('chartAcertos') as HTMLCanvasElement | null;
    const pts = document.getElementById('chartPontos') as HTMLCanvasElement | null;
    if (eng) {
      this.charts.push(new Chart(eng, {
        type: 'line',
        data: {
          labels: d.engajamento.minutos.map(m => `${m}min`),
          datasets: [
            { label: 'Controle', data: d.engajamento.controle, borderColor: '#9aa1b0', borderDash: [5, 4], tension: .3, spanGaps: true },
            { label: 'Intervenção', data: d.engajamento.intervencao, borderColor: '#1f6f54', backgroundColor: 'rgba(31,111,84,.08)', fill: true, tension: .3, spanGaps: true }
          ]
        },
        options: { scales: { y: { min: 0, max: 100 } } }
      }));
    }
    if (ace) {
      this.charts.push(new Chart(ace, {
        type: 'bar',
        data: {
          labels: d.acertos_por_questao.map(q => q.questao),
          datasets: [{ label: 'Acerto (%)', data: d.acertos_por_questao.map(q => q.acerto), backgroundColor: '#1f6f54', borderRadius: 6 }]
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } }
      }));
    }
    if (pts) {
      this.charts.push(new Chart(pts, {
        type: 'scatter',
        data: { datasets: [{ label: 'Sessão', data: d.pontos.map(p => ({ x: p.focus, y: p.acerto })), backgroundColor: 'rgba(31,111,84,.65)', pointRadius: 6 }] },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: { title: { display: true, text: 'focusScore (%)' }, min: 0, max: 100 },
            y: { title: { display: true, text: 'accuracyRate (%)' }, min: 0, max: 100 }
          }
        }
      }));
    }
  }
}
