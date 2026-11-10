import { Component, OnDestroy, OnInit, inject, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { corCadeira, inicial } from '../cores';
import { ApiService, Cadeira, Material, Questao, TelemetriaItem } from '../services/api.service';
import { VisionService } from '../services/vision.service';
import { YoloService } from '../services/yolo.service';
import { CodigoPipe } from '../codigo.pipe';

@Component({
  selector: 'app-estudante',
  imports: [RouterLink, CodigoPipe],
  templateUrl: './estudante.component.html',
  styleUrl: './estudante.component.css'
})
export class EstudanteComponent implements OnInit, OnDestroy {
  api = inject(ApiService);
  vision = inject(VisionService);
  yolo = inject(YoloService);
  private route = inject(ActivatedRoute);

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
  explicacaoEscolhida = signal('');
  sequencia = signal(0);
  xpGanho = signal(0);
  xpSessao = signal(0);
  melhorSequencia = signal(0);
  metaBatida = signal(false);
  respondidasHoje = signal(0);
  metaDiaria = signal(10);
  respondidas = signal(0);
  acertos = signal(0);
  monitorando = signal(false);
  explicarCamera = signal(false);
  modoRevisao = signal(false);

  nivel = signal('Intermediário');
  objetivo = signal('Revisão para prova');
  tempo = signal('15 min');
  materialTexto = signal('');
  gerandoEstudo = signal(false);

  cadeiraNome = computed(() => this.cadeiras().find(c => c.id === this.cadeiraId())?.nome ?? '');
  pct = computed(() => this.respondidas() ? Math.round(100 * this.acertos() / this.respondidas()) : 0);
  // O foco só é medido durante o estudo/questionário; fora disso não exibe número.
  focoExibido = computed<number | null>(() =>
    this.vision.ativo() && (this.fase() === 'quiz' || this.fase() === 'estudo') ? this.vision.foco() : null);
  corFoco = computed(() => {
    const v = this.focoExibido();
    if (v === null) return '#2e2e35';
    return v >= 60 ? '#69db7c' : v >= 40 ? '#ffa94d' : '#ff6b6b';
  });
  circ = 2 * Math.PI * 63;

  private sessaoId: number | null = null;
  private fila: Questao[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private segundos = 0;
  private buffer: TelemetriaItem[] = [];
  private eventosEnviados = 0;

  ngOnInit() {
    this.api.progresso().subscribe({
      next: p => { this.respondidasHoje.set(p.respondidas_hoje); this.metaDiaria.set(p.meta_diaria); },
      error: () => {}
    });
    this.api.listarCadeiras().subscribe(cs => this.cadeiras.set(cs));
    const id = Number(this.route.snapshot.queryParamMap.get('cadeira'));
    if (id) this.abrirCadeira(id);
  }

  ngOnDestroy() {
    if (this.timer) clearInterval(this.timer);
    this.vision.parar();
    this.yolo.parar();
  }

  letra(i: number) {
    return String.fromCharCode(97 + i);
  }

  inicial = inicial;
  corCadeira = corCadeira;

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
    if (this.monitorando()) this.desativarMonitor();
    this.fase.set('prefs');
  }

  comecar() {
    if (this.selMateriais().size === 0) return;
    const modo = this.vision.ativo() ? 'camera' : 'simulado';
    this.carregando.set(true);
    this.erro.set('');
    this.respondidas.set(0);
    this.sequencia.set(0);
    this.xpSessao.set(0);
    this.melhorSequencia.set(0);
    this.acertos.set(0);
    this.fila = [];
    this.modoRevisao.set(false);
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

  revisarErros() {
    this.erro.set('');
    this.api.listarErros(this.cadeiraId(), 20).subscribe({
      next: qs => {
        if (!qs.length) {
          this.erro.set('Você ainda não tem erros para revisar nesta cadeira.');
          return;
        }
        const ids = this.materiais().map(m => m.id);
        const modo = this.vision.ativo() ? 'camera' : 'simulado';
        this.api.iniciarSessao(this.cadeiraId(), modo, ids).subscribe({
          next: r => {
            this.sessaoId = r.sessao_id;
            this.modoRevisao.set(true);
            this.fila = qs;
            this.respondidas.set(0);
            this.sequencia.set(0);
            this.xpSessao.set(0);
            this.melhorSequencia.set(0);
            this.acertos.set(0);
            this.fase.set('quiz');
            this.timer = setInterval(() => this.tick(), 1000);
            this.mostrar(this.fila.shift()!);
          },
          error: e => this.erro.set(e.error?.detail ?? 'Falha ao iniciar a revisão')
        });
      },
      error: e => this.erro.set(e.error?.detail ?? 'Falha ao carregar os erros')
    });
  }

  carregarProxima() {
    if (!this.sessaoId) return;
    if (this.fila.length) {
      this.mostrar(this.fila.shift()!);
      if (!this.modoRevisao()) this.prefetch();
      return;
    }
    if (this.modoRevisao()) {
      this.encerrar();
      return;
    }
    this.carregando.set(true);
    this.erro.set('');
    this.api.loteQuestoes(this.sessaoId, this.idsSelecionados(), 5).subscribe({
      next: qs => {
        this.fila = qs;
        this.carregando.set(false);
        if (this.fila.length) this.mostrar(this.fila.shift()!);
        else this.erro.set('Não foi possível gerar questões.');
      },
      error: e => {
        this.carregando.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao gerar a questão');
      }
    });
  }

  private mostrar(q: Questao) {
    this.questao.set(q);
    this.escolhida.set(null);
    this.respondida.set(false);
    this.acertou.set(false);
    this.justificativa.set('');
    this.explicacaoEscolhida.set('');
    this.xpGanho.set(0);
    this.metaBatida.set(false);
  }

  private prefetch() {
    if (this.fila.length > 1 || !this.sessaoId) return;
    this.api.loteQuestoes(this.sessaoId, this.idsSelecionados(), 5).subscribe({
      next: qs => this.fila.push(...qs),
      error: () => {}
    });
  }

  responder(i: number) {
    if (!this.sessaoId || this.respondida() || !this.questao()) return;
    this.api.responder(this.sessaoId, this.questao()!.id, i).subscribe(r => {
      this.escolhida.set(i);
      this.respondida.set(true);
      this.acertou.set(r.acertou);
      this.justificativa.set(r.justificativa);
      this.explicacaoEscolhida.set(r.explicacao_escolhida || '');
      this.sequencia.set(r.sequencia ?? 0);
      this.xpGanho.set(r.xp_ganho ?? 0);
      this.xpSessao.update(x => x + (r.xp_ganho ?? 0));
      this.melhorSequencia.update(m => Math.max(m, r.sequencia ?? 0));
      this.metaBatida.set(!!r.meta_batida);
      if (r.respondidas_hoje !== undefined) this.respondidasHoje.set(r.respondidas_hoje);
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
    // O monitoramento vale só durante a sessão: encerrou, desliga a câmera.
    if (this.monitorando()) this.desativarMonitor();
    this.fase.set('fim');
  }

  voltar() {
    this.fase.set('selecao');
    this.questao.set(null);
    this.sessaoId = null;
    this.segundos = 0;
    this.fila = [];
    this.modoRevisao.set(false);
  }

  /** Antes de ligar a câmera, explica o que é medido e pede a confirmação do estudante. */
  ativarCamera() {
    this.explicarCamera.set(true);
  }

  confirmarCamera() {
    this.explicarCamera.set(false);
    this.iniciarCamera();
  }

  private async iniciarCamera() {
    if (!this.cam) return;
    const ok = await this.vision.iniciar(this.cam.nativeElement);
    if (ok) {
      this.monitorando.set(true);
      this.yolo.iniciar(this.cam.nativeElement);
    }
  }

  desativarMonitor() {
    this.vision.parar();
    this.yolo.parar();
    this.monitorando.set(false);
  }
}
