import { Component, OnDestroy, OnInit, inject, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { ApiService, Cadeira, Material, Questao, TelemetriaItem } from '../services/api.service';
import { VisionService } from '../services/vision.service';
import { YoloService } from '../services/yolo.service';

@Component({
  selector: 'app-estudante',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Questionário</div>
        <h2>{{ fase() === 'selecao' && !cadeiraId() ? 'Escolha a cadeira' : (cadeiraNome() || 'Estudo') }}</h2>
        <p>Escolha a cadeira, marque os PDFs que quer praticar e responda a um fluxo contínuo de questões geradas a partir deles.</p>
      </div>

      @if (fase() === 'selecao') {
        @if (!cadeiraId()) {
          @if (cadeiras().length === 0) {
            <p class="vazio">Nenhuma cadeira disponível. Peça ao professor para criar uma e enviar os PDFs.</p>
          } @else {
            <div class="grade">
              @for (c of cadeiras(); track c.id) {
                <button class="curso" (click)="abrirCadeira(c.id)">
                  <div class="banner" [style.background]="corCadeira(c.id)"><span>{{ inicial(c.nome) }}</span></div>
                  <div class="curso-nome">{{ c.nome }}</div>
                </button>
              }
            </div>
          }
        } @else {
          <button class="voltar" (click)="abrirCadeira(0)">← Todas as cadeiras</button>
          @if (materiais().length === 0) {
            <p class="vazio">Esta cadeira ainda não tem PDFs. Peça ao professor para enviar.</p>
          } @else {
            <div class="barra-sel">
              <span>{{ selMateriais().size }} de {{ materiais().length }} PDFs</span>
              <button class="btn-link" (click)="alternarTodos()">{{ selMateriais().size === materiais().length ? 'Limpar' : 'Selecionar todos' }}</button>
            </div>
            @for (m of materiais(); track m.id) {
              <div class="pdf" [class.marcado]="selMateriais().has(m.id)" (click)="alternar(m.id)">
                <span class="check">{{ selMateriais().has(m.id) ? '✓' : '' }}</span>
                <span class="pdf-nome">{{ m.titulo }}</span>
              </div>
            }
            <div class="acoes-estudo">
              <button class="btn btn-accent" (click)="comecar()" [disabled]="carregando() || selMateriais().size === 0">
                {{ carregando() ? 'Preparando…' : 'Questionário' }}
              </button>
              <button class="btn btn-ghost" (click)="fase.set('prefs')" [disabled]="selMateriais().size === 0">
                Material de estudo
              </button>
            </div>
            @if (erro()) { <p class="erro">{{ erro() }}</p> }
          }
        }
      }

      @if (fase() === 'prefs') {
        <button class="voltar" (click)="fase.set('selecao')">← PDFs</button>
        <div class="cartao prefs">
          <p class="prefs-intro">Ajuste o material ao seu momento — as respostas guiam a explicação gerada.</p>
          <label>Seu nível na matéria
            <select [value]="nivel()" (change)="nivel.set($any($event.target).value)">
              <option value="Iniciante">Iniciante</option>
              <option value="Intermediário">Intermediário</option>
              <option value="Avançado">Avançado</option>
            </select>
          </label>
          <label>Objetivo
            <select [value]="objetivo()" (change)="objetivo.set($any($event.target).value)">
              <option value="Primeiro contato">Primeiro contato com o assunto</option>
              <option value="Revisão para prova">Revisão para prova</option>
              <option value="Aprofundar">Aprofundar o conhecimento</option>
            </select>
          </label>
          <label>Tempo disponível
            <select [value]="tempo()" (change)="tempo.set($any($event.target).value)">
              <option value="5 min">~5 min (bem resumido)</option>
              <option value="15 min">~15 min</option>
              <option value="30+ min">30+ min (completo)</option>
            </select>
          </label>
          <button class="btn btn-accent" (click)="gerarEstudo()" [disabled]="gerandoEstudo()">
            {{ gerandoEstudo() ? 'Gerando material…' : 'Gerar material de estudo' }}
          </button>
          @if (erro()) { <p class="erro">{{ erro() }}</p> }
        </div>
      }

      @if (fase() === 'estudo') {
        <div class="topo-quiz">
          <div class="contador">Material de estudo</div>
          <div class="acoes-topo">
            @if (!monitorando()) {
              <button class="btn-link" (click)="ativarCamera()">Ativar foco (câmera)</button>
            } @else {
              <span class="foco" [class.disperso]="focoExibido() !== null && focoExibido()! < 60">Foco: {{ focoExibido() ?? '—' }}</span>
            }
            <button class="btn btn-ghost btn-mini" (click)="sairEstudo()">Voltar</button>
          </div>
        </div>
        <div class="cartao material">
          <pre class="texto-estudo">{{ materialTexto() }}</pre>
        </div>
      }

      @if (fase() === 'quiz') {
        <div class="topo-quiz">
          <div class="contador"><b>{{ respondidas() }}</b> respondidas · <b>{{ acertos() }}</b> certas
            @if (respondidas() > 0) { <span class="pct">({{ pct() }}%)</span> }
          </div>
          <div class="acoes-topo">
            @if (!monitorando()) {
              <button class="btn-link" (click)="ativarCamera()">Ativar câmera</button>
            } @else {
              <span class="foco">Foco: {{ focoExibido() ?? '—' }}</span>
            }
            <button class="btn btn-ghost btn-mini" (click)="encerrar()">Encerrar</button>
          </div>
        </div>

        @if (carregando()) {
          <div class="cartao carregando">Gerando próxima questão…</div>
        } @else if (questao()) {
          <div class="cartao questao">
            <h4>{{ questao()!.pergunta }}</h4>
            @for (op of questao()!.opcoes; track $index) {
              <button class="opt"
                [class.acerto]="respondida() && $index === questao()!.correta"
                [class.erro]="respondida() && escolhida() === $index && !acertou()"
                [disabled]="respondida()"
                (click)="responder($index)">{{ letra($index) }}) {{ op }}</button>
            }
            @if (respondida()) {
              <p class="feedback" [class.ok]="acertou()" [class.nok]="!acertou()">
                {{ acertou() ? 'Correto. ' : 'Não foi dessa vez. ' }}{{ justificativa() }}
              </p>
              <button class="btn btn-accent proxima" (click)="proxima()">Próxima questão →</button>
            }
          </div>
        } @else if (erro()) {
          <div class="cartao"><p class="erro" style="margin:0">{{ erro() }}</p></div>
        }
      }

      @if (fase() === 'fim') {
        <div class="fim">
          <h3>Questionário encerrado</h3>
          <p>{{ respondidas() }} respondidas · {{ acertos() }} certas{{ respondidas() > 0 ? ' (' + pct() + '%)' : '' }}</p>
          <button class="btn btn-ghost btn-mini" (click)="voltar()">Voltar ao início</button>
        </div>
      }

      <video #cam muted playsinline style="display:none"></video>
    </div>
  `,
  styles: `
    .grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}
    .curso{text-align:left;background:var(--surface);border:1px solid var(--linha);border-radius:4px;overflow:hidden;padding:0;transition:border-color .15s,transform .15s}
    .curso:hover{border-color:var(--accent);transform:translateY(-2px)}
    .banner{height:92px;display:flex;align-items:center;justify-content:center}
    .banner span{font-size:32px;font-weight:700;color:rgba(255,255,255,.92)}
    .curso-nome{padding:13px 15px;font-weight:600;font-size:14px}
    .voltar{color:var(--ink-soft);font-weight:600;font-size:13px;margin-bottom:16px}
    .voltar:hover{color:var(--ink)}
    .barra-sel{display:flex;justify-content:space-between;align-items:center;margin:4px 0 12px;font-size:13px;color:var(--ink-soft)}
    .btn-link{color:var(--accent);font-weight:600;font-size:13px}
    .pdf{display:flex;align-items:center;gap:14px;background:var(--surface);border:1px solid var(--linha);border-radius:4px;padding:14px 16px;margin-bottom:8px;cursor:pointer;transition:border-color .15s,background .15s}
    .pdf:hover{border-color:var(--accent)}
    .pdf.marcado{border-color:var(--accent);background:var(--accent-soft)}
    .pdf .check{width:22px;height:22px;border-radius:4px;border:1px solid var(--linha);display:grid;place-items:center;color:var(--accent);font-weight:700;flex-shrink:0}
    .pdf.marcado .check{border-color:var(--accent)}
    .pdf-nome{font-size:14px;font-weight:500}
    .acoes-estudo{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
    .prefs label{margin-bottom:14px}
    .prefs select{display:block;margin-top:6px;width:100%;max-width:360px}
    .prefs-intro{color:var(--ink-soft);font-size:13.5px;margin-bottom:16px}
    .material{padding:26px 30px}
    .texto-estudo{font-family:inherit;white-space:pre-wrap;font-size:15px;line-height:1.7;color:#cfd3dc}
    .topo-quiz{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
    .contador{font-size:14px;color:var(--ink-soft)}
    .contador b{color:var(--ink)}
    .pct{color:var(--accent)}
    .acoes-topo{display:flex;align-items:center;gap:14px}
    .foco{font-family:var(--mono);font-size:12px;color:var(--ink-soft)}
    .carregando{color:var(--ink-soft);text-align:center;padding:40px}
    .questao h4{font-size:16px;margin-bottom:16px;line-height:1.5}
    .opt{display:block;width:100%;text-align:left;padding:12px 15px;border-radius:4px;background:var(--surface-2);border:1px solid var(--linha);margin-bottom:9px;color:var(--ink)}
    .opt:hover:not(:disabled){border-color:var(--accent)}
    .opt.acerto{border-color:var(--accent);background:var(--accent-soft);font-weight:600}
    .opt.erro{border-color:var(--erro);background:var(--erro-soft)}
    .feedback{font-size:14px;padding:12px 15px;border-radius:4px;margin:6px 0 0}
    .feedback.ok{background:var(--accent-soft);color:var(--accent)}
    .feedback.nok{background:var(--erro-soft);color:var(--erro)}
    .proxima{margin-top:16px}
    .fim{text-align:center;padding:40px;border:1px dashed var(--accent);border-radius:4px;margin-top:14px}
    .fim h3{color:var(--accent);margin-bottom:8px}
    .fim p{color:var(--ink-soft);margin-bottom:16px}
  `
})
export class EstudanteComponent implements OnInit, OnDestroy {
  api = inject(ApiService);
  vision = inject(VisionService);
  yolo = inject(YoloService);

  @ViewChild('cam') cam?: ElementRef<HTMLVideoElement>;

  fase = signal<'selecao' | 'prefs' | 'estudo' | 'quiz' | 'fim'>('selecao');
  cadeiras = signal<Cadeira[]>([]);
  cadeiraId = signal(0);
  materiais = signal<Material[]>([]);
  selMateriais = signal<Set<number>>(new Set());

  carregando = signal(false);
  erro = signal('');
  questao = signal<Questao | null>(null);
  escolhida = signal<number | null>(null);
  respondida = signal(false);
  acertou = signal(false);
  justificativa = signal('');
  respondidas = signal(0);
  acertos = signal(0);
  monitorando = signal(false);

  nivel = signal('Intermediário');
  objetivo = signal('Revisão para prova');
  tempo = signal('15 min');
  materialTexto = signal('');
  gerandoEstudo = signal(false);

  cadeiraNome = computed(() => this.cadeiras().find(c => c.id === this.cadeiraId())?.nome ?? '');
  pct = computed(() => this.respondidas() ? Math.round(100 * this.acertos() / this.respondidas()) : 0);
  focoExibido = computed<number | null>(() => (this.vision.ativo() ? this.vision.foco() : null));

  private sessaoId: number | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private segundos = 0;
  private buffer: TelemetriaItem[] = [];
  private eventosEnviados = 0;

  ngOnInit() {
    this.api.listarCadeiras().subscribe(cs => this.cadeiras.set(cs));
  }

  ngOnDestroy() {
    if (this.timer) clearInterval(this.timer);
    this.vision.parar();
    this.yolo.parar();
  }

  letra(i: number) {
    return String.fromCharCode(97 + i);
  }

  inicial(nome: string) {
    return (nome.trim().charAt(0) || '?').toUpperCase();
  }

  corCadeira(id: number) {
    const h = (id * 47) % 360;
    return `hsl(${h},38%,38%)`;
  }

  abrirCadeira(id: number) {
    this.cadeiraId.set(id);
    this.selMateriais.set(new Set());
    this.materiais.set([]);
    this.erro.set('');
    if (id) this.api.listarMateriais(id).subscribe(ms => this.materiais.set(ms));
  }

  alternar(id: number) {
    const novo = new Set(this.selMateriais());
    if (novo.has(id)) novo.delete(id); else novo.add(id);
    this.selMateriais.set(novo);
  }

  alternarTodos() {
    if (this.selMateriais().size === this.materiais().length) {
      this.selMateriais.set(new Set());
    } else {
      this.selMateriais.set(new Set(this.materiais().map(m => m.id)));
    }
  }

  private idsSelecionados() {
    return [...this.selMateriais()];
  }

  gerarEstudo() {
    if (this.selMateriais().size === 0) return;
    this.gerandoEstudo.set(true);
    this.erro.set('');
    this.api.gerarEstudo(this.cadeiraId(), this.idsSelecionados(), this.nivel(), this.objetivo(), this.tempo()).subscribe({
      next: r => {
        this.materialTexto.set(r.texto);
        this.gerandoEstudo.set(false);
        this.fase.set('estudo');
        this.iniciarSessaoLeitura();
      },
      error: e => {
        this.gerandoEstudo.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao gerar o material de estudo');
      }
    });
  }

  private iniciarSessaoLeitura() {
    const modo = this.vision.ativo() ? 'camera' : 'simulado';
    this.api.iniciarSessao(this.cadeiraId(), modo, this.idsSelecionados()).subscribe(r => {
      this.sessaoId = r.sessao_id;
      this.segundos = 0;
      this.timer = setInterval(() => this.tick(), 1000);
    });
  }

  sairEstudo() {
    if (this.timer) clearInterval(this.timer);
    if (this.sessaoId) {
      if (this.buffer.length) {
        this.api.enviarTelemetria(this.sessaoId, this.buffer).subscribe();
        this.buffer = [];
      }
      this.api.encerrarSessao(this.sessaoId).subscribe();
      this.sessaoId = null;
    }
    this.fase.set('prefs');
  }

  comecar() {
    if (this.selMateriais().size === 0) return;
    const modo = this.vision.ativo() ? 'camera' : 'simulado';
    this.carregando.set(true);
    this.erro.set('');
    this.respondidas.set(0);
    this.acertos.set(0);
    this.api.iniciarSessao(this.cadeiraId(), modo, this.idsSelecionados()).subscribe({
      next: r => {
        this.sessaoId = r.sessao_id;
        this.fase.set('quiz');
        this.timer = setInterval(() => this.tick(), 1000);
        this.carregarProxima();
      },
      error: e => {
        this.carregando.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao iniciar o questionário');
      }
    });
  }

  carregarProxima() {
    if (!this.sessaoId) return;
    this.carregando.set(true);
    this.erro.set('');
    this.api.proximaQuestao(this.sessaoId, this.idsSelecionados()).subscribe({
      next: q => {
        this.questao.set(q);
        this.escolhida.set(null);
        this.respondida.set(false);
        this.acertou.set(false);
        this.justificativa.set('');
        this.carregando.set(false);
      },
      error: e => {
        this.carregando.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao gerar a questão');
      }
    });
  }

  responder(i: number) {
    if (!this.sessaoId || this.respondida() || !this.questao()) return;
    this.api.responder(this.sessaoId, this.questao()!.id, i).subscribe(r => {
      this.escolhida.set(i);
      this.respondida.set(true);
      this.acertou.set(r.acertou);
      this.justificativa.set(r.justificativa);
      this.respondidas.update(n => n + 1);
      if (r.acertou) this.acertos.update(n => n + 1);
    });
  }

  proxima() {
    this.carregarProxima();
  }

  private tick() {
    this.segundos += 1;
    if (this.segundos % 5 === 0) {
      const novos = this.yolo.eventos() - this.eventosEnviados;
      this.eventosEnviados = this.yolo.eventos();
      this.buffer.push({
        t_offset: this.segundos,
        focus: this.focoExibido() ?? 0,
        phone_eventos: Math.max(0, novos),
        modo: this.vision.ativo() ? 'camera' : 'simulado'
      });
    }
    if (this.segundos % 15 === 0 && this.buffer.length && this.sessaoId) {
      const lote = [...this.buffer];
      this.buffer = [];
      this.api.enviarTelemetria(this.sessaoId, lote).subscribe();
    }
  }

  encerrar() {
    if (this.sessaoId) {
      if (this.buffer.length) {
        this.api.enviarTelemetria(this.sessaoId, this.buffer).subscribe();
        this.buffer = [];
      }
      this.api.encerrarSessao(this.sessaoId).subscribe();
    }
    if (this.timer) clearInterval(this.timer);
    this.fase.set('fim');
  }

  voltar() {
    this.fase.set('selecao');
    this.questao.set(null);
    this.sessaoId = null;
    this.segundos = 0;
  }

  async ativarCamera() {
    if (!this.cam) return;
    const ok = await this.vision.iniciar(this.cam.nativeElement);
    if (ok) this.monitorando.set(true);
  }
}
