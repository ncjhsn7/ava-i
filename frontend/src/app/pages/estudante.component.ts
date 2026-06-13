import { Component, OnDestroy, OnInit, inject, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { ApiService, Material, Questao, TelemetriaItem } from '../services/api.service';
import { VisionService } from '../services/vision.service';
import { YoloService } from '../services/yolo.service';

interface Bloco {
  trecho: string;
  questao: Questao;
  respondida: boolean;
  escolhida: number | null;
  acertou: boolean | null;
  justificativa: string;
}

@Component({
  selector: 'app-estudante',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Módulo 2 · Sessão de estudo inteligente</div>
        <h2>{{ material()?.titulo || 'Sessão de estudo' }}</h2>
        <p>O monitoramento roda inteiramente neste navegador; apenas métricas agregadas são enviadas ao servidor.</p>
      </div>

      @if (fase() === 'selecao') {
        <div class="cartao">
          @if (materiais().length === 0) {
            <p>Nenhum material publicado ainda. Peça ao docente para preparar e publicar um material.</p>
          } @else {
            <label>Material
              <select [value]="materialId()" (change)="materialId.set(+$any($event.target).value)">
                @for (m of materiais(); track m.id) {
                  <option [value]="m.id">{{ m.titulo }}</option>
                }
              </select>
            </label>
            <label>Condição experimental
              <select [value]="condicao()" (change)="condicao.set($any($event.target).value)">
                <option value="intervencao">Intervenção — leitura com checkpoints</option>
                <option value="controle">Controle — leitura sem questões</option>
              </select>
            </label>
            <button class="btn btn-verde" (click)="comecar()">Iniciar sessão</button>
          }
        </div>
      }

      @if (fase() === 'sessao' || fase() === 'fim') {
        <div class="sessao">
          <article class="leitura" [class.esmaecida]="focoExibido() < 45">
            @for (bloco of blocos(); track bloco.questao.id; let i = $index) {
              @if (i <= blocoAtual()) {
                <section>
                  <h3>Trecho {{ i + 1 }}</h3>
                  <p class="texto">{{ bloco.trecho }}</p>
                  @if (condicao() === 'intervencao' && i === blocoAtual() && fase() === 'sessao') {
                    <div class="checkpoint">
                      <div class="cp-selo">Ponto de verificação</div>
                      <h4>{{ bloco.questao.pergunta }}</h4>
                      @for (opcao of bloco.questao.opcoes; track $index) {
                        <button class="cp-opt"
                          [class.acerto]="bloco.respondida && $index === bloco.questao.correta"
                          [class.erro]="bloco.respondida && bloco.escolhida === $index && !bloco.acertou"
                          [disabled]="bloco.respondida"
                          (click)="responder(bloco, $index)">{{ letra($index) }}) {{ opcao }}</button>
                      }
                      @if (bloco.respondida) {
                        <p class="feedback" [class.ok]="bloco.acertou" [class.nok]="!bloco.acertou">
                          {{ bloco.acertou ? 'Correto. ' : 'Não foi dessa vez. ' }}{{ bloco.justificativa }}
                        </p>
                      }
                    </div>
                  }
                </section>
              }
            }
            @if (condicao() === 'controle' && fase() === 'sessao') {
              <button class="btn btn-verde" (click)="encerrar()">Concluir leitura</button>
            }
            @if (fase() === 'fim') {
              <div class="fim">
                <h3>Sessão concluída</h3>
                <p>Telemetria agregada enviada ao backend. Nenhum quadro de vídeo saiu desta máquina.</p>
              </div>
            }
          </article>

          <aside class="painel">
            <div class="instrumento">
              <div class="rotulo">Monitoramento local
                <span class="modo" [class.cam]="vision.ativo()" [class.degradado]="vision.erro()">
                  {{ vision.ativo() ? (vision.calibrado() ? 'câmera real' : 'calibrando…') : (vision.erro() ? 'degradado' : 'simulado') }}
                </span>
              </div>
              <div class="estado" [class.atento]="focoExibido() >= 60" [class.disperso]="focoExibido() < 60">
                ● {{ focoExibido() >= 60 ? 'ATENTO' : 'DISPERSO' }}
              </div>
              <div class="medidor">
                <svg width="130" height="130">
                  <circle class="fundo" cx="65" cy="65" r="55"></circle>
                  <circle class="arco" cx="65" cy="65" r="55"
                    [attr.stroke]="focoExibido() >= 60 ? '#3ddc97' : focoExibido() >= 40 ? '#f0b35c' : '#e96a6a'"
                    stroke-dasharray="345.6"
                    [attr.stroke-dashoffset]="345.6 * (1 - focoExibido() / 100)"></circle>
                </svg>
                <div class="valor"><b>{{ focoExibido() }}</b><span>focusScore</span></div>
              </div>
              <div class="linha"><span>EAR</span><b>{{ vision.earAtual() ?? '—' }}</b></div>
              <div class="linha"><span>Eventos de celular</span><b>{{ yolo.eventos() }}</b></div>
              <div class="linha"><span>Detector YOLO</span><b>{{ yolo.disponivel() ? (yolo.celularVisivel() ? 'celular!' : 'ativo') : 'inativo' }}</b></div>
              <div class="linha"><span>Tempo</span><b>{{ relogio() }}</b></div>
              <button class="btn btn-mini acao" (click)="ativarCamera()" [disabled]="vision.ativo()">Ativar câmera (MediaPipe)</button>
              <button class="btn btn-mini acao" (click)="ativarYolo()" [disabled]="!vision.ativo() || yolo.disponivel()">Ativar detector de celular (YOLO)</button>
              @if (vision.erro()) { <p class="aviso">{{ vision.erro() }}</p> }
              <video #cam muted playsinline [style.display]="vision.ativo() ? 'block' : 'none'"></video>
            </div>
            <div class="cartao privacidade">
              <b>Privacidade por arquitetura</b>
              O vídeo é processado pelo MediaPipe e pelo YOLOv8 dentro do seu navegador, conforme a LGPD.
            </div>
          </aside>
        </div>
      }
    </div>
  `,
  styles: `
    label{display:block;margin-bottom:14px;font-weight:600;font-size:13px}
    label select{display:block;margin-top:6px;min-width:320px}
    .sessao{display:grid;grid-template-columns:1fr 300px;gap:28px;align-items:start;margin-top:20px}
    .leitura{background:var(--surface);border:1px solid var(--linha);border-radius:14px;padding:38px 44px;transition:filter .6s}
    .leitura.esmaecida{filter:saturate(.6) brightness(.96)}
    .leitura h3{color:var(--verde);margin:22px 0 10px;font-size:18px}
    .texto{font-size:16px;line-height:1.75;max-width:64ch;white-space:pre-line}
    .checkpoint{border:1.5px solid var(--verde);border-radius:14px;padding:20px;margin:22px 0;background:var(--verde-claro)}
    .cp-selo{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--verde);margin-bottom:8px}
    .checkpoint h4{margin-bottom:12px}
    .cp-opt{display:block;width:100%;text-align:left;padding:10px 14px;border-radius:9px;background:var(--surface);border:1.5px solid var(--linha);margin-bottom:8px}
    .cp-opt.acerto{border-color:var(--verde);background:var(--verde-claro);font-weight:600}
    .cp-opt.erro{border-color:var(--vinho);background:var(--vinho-claro)}
    .feedback{font-size:14px;padding:10px 14px;border-radius:9px}
    .feedback.ok{background:var(--verde-claro);color:var(--verde)}
    .feedback.nok{background:var(--vinho-claro);color:var(--vinho)}
    .fim{text-align:center;padding:30px;border:1.5px dashed var(--verde);border-radius:14px;margin-top:14px}
    .fim h3{color:var(--verde)}
    .painel{position:sticky;top:78px;display:flex;flex-direction:column;gap:14px}
    .instrumento{background:var(--ink);color:#e8eaf0;border-radius:14px;padding:20px;font-family:var(--mono)}
    .rotulo{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8b93a7;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center}
    .modo{font-size:10px;padding:3px 9px;border-radius:99px;background:#2e3850;color:#aeb8d0}
    .modo.cam{background:#1f6f54;color:#dff3ea}
    .modo.degradado{background:#5a4413;color:#f3dfb3}
    .estado{text-align:center;font-size:12px;padding:6px;border-radius:8px;margin-bottom:10px}
    .estado.atento{background:#163b2e;color:#3ddc97}
    .estado.disperso{background:#4a2e10;color:#f0b35c}
    .medidor{position:relative;display:flex;justify-content:center;margin-bottom:12px}
    .medidor svg{transform:rotate(-90deg)}
    .fundo{fill:none;stroke:#2e3850;stroke-width:9}
    .arco{fill:none;stroke-width:9;stroke-linecap:round;transition:stroke-dashoffset .5s}
    .valor{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
    .valor b{font-size:26px;color:#fff;display:block}
    .valor span{font-size:10px;color:#8b93a7;text-transform:uppercase}
    .linha{display:flex;justify-content:space-between;font-size:13px;padding:7px 0;border-top:1px solid #2e3850}
    .linha b{color:#fff;font-weight:500}
    .acao{width:100%;margin-top:10px;background:#2e3850;color:#cdd5e6}
    .aviso{font-size:11.5px;color:#f3dfb3;margin-top:10px}
    video{width:100%;border-radius:10px;margin-top:10px;background:#000}
    .privacidade{font-size:12.5px;color:var(--ink-soft)}
    .privacidade b{color:var(--verde);display:block;margin-bottom:4px}
    @media(max-width:920px){.sessao{grid-template-columns:1fr}.painel{position:static}}
  `
})
export class EstudanteComponent implements OnInit, OnDestroy {
  api = inject(ApiService);
  vision = inject(VisionService);
  yolo = inject(YoloService);

  @ViewChild('cam') cam?: ElementRef<HTMLVideoElement>;

  fase = signal<'selecao' | 'sessao' | 'fim'>('selecao');
  materiais = signal<Material[]>([]);
  materialId = signal(0);
  condicao = signal<'intervencao' | 'controle'>('intervencao');
  blocos = signal<Bloco[]>([]);
  blocoAtual = signal(0);
  segundos = signal(0);
  focoSimulado = signal(80);

  material = computed(() => this.materiais().find(m => m.id === this.materialId()));
  focoExibido = computed(() => (this.vision.ativo() ? this.vision.foco() : Math.round(this.focoSimulado())));
  relogio = computed(() => {
    const s = this.segundos();
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  });

  private sessaoId: number | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private bufferTelemetria: TelemetriaItem[] = [];
  private eventosEnviados = 0;

  ngOnInit() {
    this.api.listarMateriais('publicado').subscribe(ms => {
      this.materiais.set(ms);
      if (ms.length) this.materialId.set(ms[0].id);
    });
  }

  ngOnDestroy() {
    if (this.timer) clearInterval(this.timer);
    this.vision.parar();
    this.yolo.parar();
  }

  letra(i: number) {
    return String.fromCharCode(97 + i);
  }

  comecar() {
    this.api.listarQuestoes(this.materialId(), 'aprovada').subscribe(qs => {
      this.blocos.set(qs.map(q => ({
        trecho: q.chunk_fonte,
        questao: q,
        respondida: false,
        escolhida: null,
        acertou: null,
        justificativa: ''
      })));
      const modo = this.vision.ativo() ? 'camera' : 'simulado';
      this.api.iniciarSessao(this.materialId(), this.condicao(), modo).subscribe(r => {
        this.sessaoId = r.id;
        this.fase.set('sessao');
        this.blocoAtual.set(this.condicao() === 'controle' ? this.blocos().length - 1 : 0);
        this.timer = setInterval(() => this.tick(), 1000);
      });
    });
  }

  private tick() {
    this.segundos.update(s => s + 1);
    if (!this.vision.ativo()) {
      const alvo = 76;
      this.focoSimulado.update(f => Math.max(25, Math.min(97, f + (alvo - f) * 0.08 + (Math.random() * 8 - 4))));
    }
    if (this.segundos() % 5 === 0) {
      const novosEventos = this.yolo.eventos() - this.eventosEnviados;
      this.eventosEnviados = this.yolo.eventos();
      this.bufferTelemetria.push({
        t_offset: this.segundos(),
        focus: this.focoExibido(),
        phone_eventos: Math.max(0, novosEventos),
        modo: this.vision.ativo() ? (this.yolo.disponivel() ? 'camera+yolo' : 'camera') : 'simulado'
      });
    }
    if (this.segundos() % 15 === 0 && this.bufferTelemetria.length && this.sessaoId) {
      const lote = [...this.bufferTelemetria];
      this.bufferTelemetria = [];
      this.api.enviarTelemetria(this.sessaoId, lote).subscribe();
    }
  }

  responder(bloco: Bloco, escolhida: number) {
    if (!this.sessaoId || bloco.respondida) return;
    this.api.responder(this.sessaoId, bloco.questao.id, escolhida).subscribe(r => {
      bloco.respondida = true;
      bloco.escolhida = escolhida;
      bloco.acertou = r.acertou;
      bloco.justificativa = r.justificativa;
      this.blocos.update(b => [...b]);
      setTimeout(() => {
        if (this.blocoAtual() + 1 < this.blocos().length) {
          this.blocoAtual.update(i => i + 1);
        } else {
          this.encerrar();
        }
      }, 1800);
    });
  }

  encerrar() {
    if (!this.sessaoId) return;
    if (this.bufferTelemetria.length) {
      this.api.enviarTelemetria(this.sessaoId, this.bufferTelemetria).subscribe();
      this.bufferTelemetria = [];
    }
    this.api.encerrarSessao(this.sessaoId).subscribe(() => this.fase.set('fim'));
    if (this.timer) clearInterval(this.timer);
  }

  async ativarCamera() {
    if (!this.cam) return;
    await this.vision.iniciar(this.cam.nativeElement);
  }

  async ativarYolo() {
    if (!this.cam) return;
    const ok = await this.yolo.iniciar(this.cam.nativeElement);
    if (!ok) this.vision.erro.set('Modelo yolov8n.onnx não encontrado em assets — detector de celular desativado (degradação graciosa).');
  }
}
