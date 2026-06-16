import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, Cadeira, Material, Pergunta } from '../services/api.service';

@Component({
  selector: 'app-professor',
  template: `
    <div class="view">
      <div class="cabecalho">
        <div class="selo">Área do professor</div>
        <h2>Cadeiras e materiais</h2>
        <p>Crie uma cadeira, envie os PDFs e gere uma questão de exemplo para verificar se o material e a IA estão gerando perguntas adequadas.</p>
      </div>

      <div class="cartao">
        <label>Nova cadeira</label>
        <div class="linha-form">
          <input type="text" [value]="novoNome()" (input)="novoNome.set($any($event.target).value)" placeholder="Ex.: Redes de Computadores">
          <button class="btn btn-accent" (click)="criarCadeira()" [disabled]="!novoNome().trim()">Criar</button>
        </div>
      </div>

      @if (cadeiras().length === 0) {
        <p class="vazio" style="margin-top:18px">Nenhuma cadeira ainda. Crie a primeira acima.</p>
      }

      @for (c of cadeiras(); track c.id) {
        <div class="cartao cadeira">
          <div class="cabeca" (click)="abrir(c)">
            <b>{{ c.nome }}</b>
            <span class="acoes-cab">
              <button class="btn-x" title="Remover cadeira" (click)="removerCadeira(c, $event)">✕</button>
              <span class="seta">{{ sel()?.id === c.id ? '▴' : '▾' }}</span>
            </span>
          </div>

          @if (sel()?.id === c.id) {
            <div class="corpo">
              <div class="bloco-upload">
                <input type="text" [value]="tituloMaterial()" (input)="tituloMaterial.set($any($event.target).value)" placeholder="Título do PDF (ex.: Capítulo 3 — SNMP)">
                <input type="file" accept="application/pdf" (change)="selecionarArquivo($event)">
                <button class="btn btn-accent btn-mini" (click)="enviar(c)" [disabled]="enviando() || !arquivo || !tituloMaterial().trim()">
                  {{ enviando() ? 'Processando…' : 'Enviar PDF' }}
                </button>
              </div>
              @if (erro()) { <p class="erro">{{ erro() }}</p> }

              @if (materiais().length) {
                <div class="rotulo-secao">PDFs ({{ materiais().length }})</div>
                @for (m of materiais(); track m.id) {
                  <div class="material-item">
                    <div class="mat-cabeca">
                      <span class="pdf-nome">{{ m.titulo }}</span>
                      <span class="mat-acoes">
                        <button class="btn btn-ghost btn-mini" (click)="verPreview(m)" [disabled]="carregando() === m.id">
                          {{ carregando() === m.id ? 'Gerando…' : 'Pré-visualizar questão' }}
                        </button>
                        <button class="btn-x" title="Remover PDF" (click)="removerMaterial(m)">✕</button>
                      </span>
                    </div>
                    @if (preview() && previewId() === m.id) {
                      <div class="preview">
                        <p class="pv-pergunta">{{ preview()!.pergunta }}</p>
                        <ol type="a">
                          @for (op of preview()!.opcoes; track $index) {
                            <li [class.certa]="$index === preview()!.correta">{{ op }}</li>
                          }
                        </ol>
                        <div class="pv-fonte">Trecho-fonte: {{ preview()!.fonte }}</div>
                      </div>
                    }
                  </div>
                }
              } @else {
                <p class="vazio">Nenhum PDF enviado ainda.</p>
              }
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .linha-form{display:flex;gap:10px;margin-top:8px}
    .linha-form input{flex:1}
    .cadeira{padding:0;overflow:hidden}
    .cabeca{display:flex;justify-content:space-between;align-items:center;padding:18px 20px;cursor:pointer}
    .cabeca b{font-size:15px}
    .acoes-cab{display:flex;align-items:center;gap:12px}
    .seta{color:var(--ink-soft)}
    .btn-x{color:var(--erro);background:none;font-size:14px;padding:4px 8px;border-radius:4px}
    .btn-x:hover{background:var(--erro-soft)}
    .corpo{padding:4px 20px 22px;border-top:1px solid var(--linha)}
    .bloco-upload{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:16px}
    .bloco-upload input[type=text]{flex:1;min-width:240px}
    .rotulo-secao{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-soft);margin:22px 0 10px}
    .material-item{background:var(--surface-2);border:1px solid var(--linha);border-radius:4px;padding:12px 14px;margin-bottom:8px}
    .mat-cabeca{display:flex;justify-content:space-between;align-items:center;gap:12px}
    .pdf-nome{font-size:14px;font-weight:500}
    .mat-acoes{display:flex;align-items:center;gap:8px}
    .preview{margin-top:12px;border-top:1px dashed var(--linha);padding-top:12px}
    .pv-pergunta{font-size:14.5px;font-weight:600;margin-bottom:6px;line-height:1.5}
    ol{margin:0 0 10px 20px}
    li{font-size:13.5px;color:var(--ink-soft);padding:2px 0}
    li.certa{color:var(--accent);font-weight:600}
    .pv-fonte{font-size:12px;color:var(--ink-soft);font-style:italic;border-left:2px solid var(--linha);padding-left:10px}
  `
})
export class ProfessorComponent implements OnInit {
  api = inject(ApiService);

  cadeiras = signal<Cadeira[]>([]);
  novoNome = signal('');
  sel = signal<Cadeira | null>(null);
  materiais = signal<Material[]>([]);
  tituloMaterial = signal('');
  enviando = signal(false);
  erro = signal('');
  preview = signal<Pergunta | null>(null);
  previewId = signal(0);
  carregando = signal(0);
  arquivo: File | null = null;

  ngOnInit() {
    this.recarregar();
  }

  recarregar() {
    this.api.listarCadeiras().subscribe(cs => this.cadeiras.set(cs));
  }

  criarCadeira() {
    const nome = this.novoNome().trim();
    if (!nome) return;
    this.api.criarCadeira(nome).subscribe(c => {
      this.novoNome.set('');
      this.recarregar();
      this.abrir(c);
    });
  }

  abrir(c: Cadeira) {
    if (this.sel()?.id === c.id) {
      this.sel.set(null);
      return;
    }
    this.sel.set(c);
    this.materiais.set([]);
    this.preview.set(null);
    this.erro.set('');
    this.api.listarMateriais(c.id).subscribe(ms => this.materiais.set(ms));
  }

  selecionarArquivo(evento: Event) {
    const alvo = evento.target as HTMLInputElement;
    this.arquivo = alvo.files?.[0] ?? null;
  }

  enviar(c: Cadeira) {
    if (!this.arquivo || !this.tituloMaterial().trim()) return;
    this.enviando.set(true);
    this.erro.set('');
    this.api.criarMaterial(c.id, this.tituloMaterial().trim(), this.arquivo).subscribe({
      next: () => {
        this.enviando.set(false);
        this.tituloMaterial.set('');
        this.arquivo = null;
        this.api.listarMateriais(c.id).subscribe(ms => this.materiais.set(ms));
      },
      error: e => {
        this.enviando.set(false);
        this.erro.set(e.error?.detail ?? 'Falha ao processar o PDF. O backend está em localhost:8000?');
      }
    });
  }

  removerMaterial(m: Material) {
    if (!confirm(`Remover o PDF "${m.titulo}"?`)) return;
    this.api.removerMaterial(m.id).subscribe(() => {
      if (this.sel()) this.api.listarMateriais(this.sel()!.id).subscribe(ms => this.materiais.set(ms));
    });
  }

  removerCadeira(c: Cadeira, ev: Event) {
    ev.stopPropagation();
    if (!confirm(`Remover a cadeira "${c.nome}" e todos os seus PDFs?`)) return;
    this.api.removerCadeira(c.id).subscribe(() => {
      if (this.sel()?.id === c.id) this.sel.set(null);
      this.recarregar();
    });
  }

  verPreview(m: Material) {
    this.carregando.set(m.id);
    this.preview.set(null);
    this.erro.set('');
    this.api.previewMaterial(m.id).subscribe({
      next: p => {
        this.preview.set(p);
        this.previewId.set(m.id);
        this.carregando.set(0);
      },
      error: e => {
        this.carregando.set(0);
        this.erro.set(e.error?.detail ?? 'Falha ao gerar a pré-visualização');
      }
    });
  }
}
