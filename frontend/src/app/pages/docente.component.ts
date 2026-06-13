import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, Material, Questao } from '../services/api.service';

@Component({
  selector: 'app-docente',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Módulo 1 · Geração de avaliações formativas</div>
        <h2>Preparar material</h2>
        <p>Envie o PDF da disciplina. As questões são geradas pelo pipeline RAG e só vão ao ar depois da sua aprovação.</p>
      </div>

      <div class="cartao formulario">
        <label>Título do material
          <input type="text" [value]="titulo()" (input)="titulo.set($any($event.target).value)" placeholder="Ex.: Redes Neurais — Capítulo 3">
        </label>
        <label>Cenário de geração
          <select [value]="cenario()" (change)="cenario.set($any($event.target).value)">
            <option value="restrito">Restrito — somente trechos do PDF</option>
            <option value="expandido">Expandido — trechos + vizinhos recuperados no ChromaDB</option>
          </select>
        </label>
        <label>Arquivo PDF
          <input type="file" accept="application/pdf" (change)="selecionarArquivo($event)">
        </label>
        <button class="btn btn-verde" (click)="enviar()" [disabled]="enviando() || !arquivo || !titulo()">
          {{ enviando() ? 'Processando — extração, chunking, embeddings, geração…' : 'Enviar e gerar questões' }}
        </button>
        @if (erro()) { <p class="erro">{{ erro() }}</p> }
      </div>

      @if (materiais().length) {
        <h3 class="subtitulo">Materiais</h3>
        @for (m of materiais(); track m.id) {
          <div class="cartao material" (click)="abrir(m)">
            <div>
              <b>{{ m.titulo }}</b>
              <span class="tag">{{ m.cenario }}</span>
              <span class="tag" [class.verde]="m.status === 'publicado'">{{ m.status }}</span>
            </div>
            <span class="abrir">{{ aberto()?.id === m.id ? '▴' : '▾' }}</span>
          </div>
          @if (aberto()?.id === m.id) {
            @for (q of questoes(); track q.id) {
              <div class="cartao questao" [class.aprovada]="q.status === 'aprovada'" [class.rejeitada]="q.status === 'rejeitada'">
                <div class="meta">
                  <span class="tag verde">gerada por RAG</span>
                  <span class="tag">{{ q.status }}</span>
                </div>
                @if (editando() === q.id) {
                  <textarea [value]="textoEdicao()" (input)="textoEdicao.set($any($event.target).value)" rows="3"></textarea>
                } @else {
                  <h4>{{ q.pergunta }}</h4>
                }
                <ol type="a">
                  @for (opcao of q.opcoes; track $index) {
                    <li [class.certa]="$index === q.correta">{{ opcao }}</li>
                  }
                </ol>
                <div class="chunk"><b>Trecho-fonte</b>{{ q.chunk_fonte }}</div>
                <div class="acoes">
                  <button class="btn btn-mini btn-verde" (click)="mudarStatus(q, 'aprovada')">Aprovar</button>
                  <button class="btn btn-mini btn-ghost" (click)="alternarEdicao(q)">{{ editando() === q.id ? 'Salvar' : 'Editar' }}</button>
                  <button class="btn btn-mini btn-ghost" (click)="mudarStatus(q, 'rejeitada')">Rejeitar</button>
                </div>
              </div>
            }
            @if (m.status !== 'publicado') {
              <button class="btn btn-verde publicar" (click)="publicar(m)">Publicar questões aprovadas</button>
            }
          }
        }
      }
    </div>
  `,
  styles: `
    .formulario label{display:block;margin-bottom:14px;font-weight:600;font-size:13px}
    .formulario input,.formulario select{display:block;margin-top:6px;min-width:340px}
    .erro{color:var(--vinho);margin-top:10px;font-size:13.5px}
    .subtitulo{margin:26px 0 12px}
    .material{display:flex;justify-content:space-between;align-items:center;cursor:pointer;margin-bottom:10px}
    .material .tag{margin-left:8px}
    .questao{margin:0 0 12px 22px;border-left:4px solid var(--linha)}
    .questao.aprovada{border-left-color:var(--verde)}
    .questao.rejeitada{opacity:.5;border-left-color:var(--vinho)}
    .meta{display:flex;gap:8px;margin-bottom:10px}
    .questao h4{margin-bottom:10px}
    .questao textarea{width:100%;margin-bottom:10px}
    ol{margin:0 0 6px 22px}
    li{font-size:14px;color:var(--ink-soft);padding:3px 0}
    li.certa{color:var(--verde);font-weight:600}
    .chunk b{font-family:var(--mono);font-style:normal;font-size:11px;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:4px;color:var(--ambar)}
    .acoes{display:flex;gap:8px}
    .publicar{margin:6px 0 18px 22px}
  `
})
export class DocenteComponent implements OnInit {
  api = inject(ApiService);

  titulo = signal('');
  cenario = signal('restrito');
  enviando = signal(false);
  erro = signal('');
  materiais = signal<Material[]>([]);
  aberto = signal<Material | null>(null);
  questoes = signal<Questao[]>([]);
  editando = signal<number | null>(null);
  textoEdicao = signal('');
  arquivo: File | null = null;

  ngOnInit() {
    this.recarregar();
  }

  recarregar() {
    this.api.listarMateriais().subscribe(ms => this.materiais.set(ms));
  }

  selecionarArquivo(evento: Event) {
    const alvo = evento.target as HTMLInputElement;
    this.arquivo = alvo.files?.[0] ?? null;
  }

  enviar() {
    if (!this.arquivo || !this.titulo()) return;
    this.enviando.set(true);
    this.erro.set('');
    this.api.criarMaterial(this.titulo(), this.cenario(), this.arquivo).subscribe({
      next: m => {
        this.enviando.set(false);
        this.titulo.set('');
        this.recarregar();
        this.abrir(m);
      },
      error: e => {
        this.enviando.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao processar o PDF. O backend está rodando em localhost:8000?');
      }
    });
  }

  abrir(m: Material) {
    if (this.aberto()?.id === m.id) {
      this.aberto.set(null);
      return;
    }
    this.aberto.set(m);
    this.api.listarQuestoes(m.id).subscribe(qs => this.questoes.set(qs));
  }

  mudarStatus(q: Questao, status: string) {
    this.api.atualizarQuestao(q.id, { status }).subscribe(novo => {
      this.questoes.update(lista => lista.map(item => (item.id === q.id ? novo : item)));
    });
  }

  alternarEdicao(q: Questao) {
    if (this.editando() === q.id) {
      this.api.atualizarQuestao(q.id, { pergunta: this.textoEdicao() }).subscribe(novo => {
        this.questoes.update(lista => lista.map(item => (item.id === q.id ? novo : item)));
        this.editando.set(null);
      });
    } else {
      this.editando.set(q.id);
      this.textoEdicao.set(q.pergunta);
    }
  }

  publicar(m: Material) {
    this.api.publicar(m.id).subscribe({
      next: () => this.recarregar(),
      error: e => this.erro.set(e.error?.detail ?? 'Falha ao publicar')
    });
  }
}
