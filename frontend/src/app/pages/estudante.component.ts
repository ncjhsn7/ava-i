import { Component, OnDestroy, OnInit, inject, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { ApiService, Cadeira, Material, Questao, TelemetriaItem } from '../services/api.service';
import { VisionService } from '../services/vision.service';
import { YoloService } from '../services/yolo.service';

@Component({
  selector: 'app-estudante',
  templateUrl: './estudante.component.html',
  styleUrl: './estudante.component.css'
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
