import { Component, OnInit, inject, signal } from '@angular/core';
import { corCadeira, inicial } from '../cores';
import { ApiService, Cadeira, Material, Pergunta } from '../services/api.service';

@Component({
  selector: 'app-professor',
  templateUrl: './docente.component.html',
  styleUrl: './docente.component.css'
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
  arquivos = signal<File[]>([]);
  arrastando = signal(false);
  progressoEnvio = signal('');

  ngOnInit() {
    this.recarregar();
  }

  inicial = inicial;
  corCadeira = corCadeira;

  recarregar() {
    this.api.listarCadeiras().subscribe(cs => {
      this.cadeiras.set(cs);
      const atual = this.sel();
      if (!atual || !cs.some(c => c.id === atual.id)) {
        this.sel.set(null);
        if (cs.length) this.abrir(cs[0]);
      }
    });
  }

  criarCadeira() {
    const nome = this.novoNome().trim();
    if (!nome) return;
    this.api.criarCadeira(nome).subscribe(c => {
      this.novoNome.set('');
      this.abrir(c);
      this.recarregar();
    });
  }

  abrir(c: Cadeira) {
    if (this.sel()?.id === c.id) return;
    this.sel.set(c);
    this.materiais.set([]);
    this.preview.set(null);
    this.erro.set('');
    this.api.listarMateriais(c.id).subscribe(ms => this.materiais.set(ms));
  }

  selecionarArquivo(evento: Event) {
    const alvo = evento.target as HTMLInputElement;
    this.adicionarArquivos(alvo.files);
    alvo.value = ''; // permite escolher o mesmo arquivo de novo
  }

  aoArrastar(ev: DragEvent) {
    ev.preventDefault();
    if (!this.enviando()) this.arrastando.set(true);
  }

  aoSairArrasto(ev: DragEvent) {
    const destino = ev.currentTarget as HTMLElement;
    if (!destino.contains(ev.relatedTarget as Node)) this.arrastando.set(false);
  }

  aoSoltar(ev: DragEvent) {
    ev.preventDefault();
    this.arrastando.set(false);
    if (!this.enviando()) this.adicionarArquivos(ev.dataTransfer?.files ?? null);
  }

  private adicionarArquivos(lista: FileList | null) {
    if (!lista) return;
    const todos = Array.from(lista);
    const pdfs = todos.filter(f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    this.erro.set(pdfs.length < todos.length ? 'Alguns arquivos foram ignorados: só PDFs são aceitos.' : '');
    const atuais = this.arquivos();
    const novos = pdfs.filter(f => !atuais.some(a => a.name === f.name && a.size === f.size));
    this.arquivos.set([...atuais, ...novos]);
  }

  removerArquivo(i: number) {
    this.arquivos.update(lista => lista.filter((_, j) => j !== i));
  }

  tituloDoArquivo(f: File) {
    return f.name.replace(/\.pdf$/i, '').replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  enviar(c: Cadeira) {
    const fila = [...this.arquivos()];
    if (!fila.length || this.enviando()) return;
    const tituloUnico = fila.length === 1 ? this.tituloMaterial().trim() : '';
    const falhas: string[] = [];
    this.enviando.set(true);
    this.erro.set('');

    const proximo = (i: number) => {
      if (i >= fila.length) {
        this.enviando.set(false);
        this.progressoEnvio.set('');
        this.tituloMaterial.set('');
        this.arquivos.set(fila.filter(f => falhas.includes(f.name)));
        if (falhas.length) this.erro.set(`Não foi possível processar: ${falhas.join(', ')}.`);
        this.api.listarMateriais(c.id).subscribe(ms => this.materiais.set(ms));
        return;
      }
      const f = fila[i];
      this.progressoEnvio.set(fila.length > 1 ? `Processando ${i + 1} de ${fila.length}…` : 'Processando…');
      this.api.criarMaterial(c.id, tituloUnico || this.tituloDoArquivo(f), f).subscribe({
        next: () => {
          this.api.listarMateriais(c.id).subscribe(ms => this.materiais.set(ms));
          proximo(i + 1);
        },
        error: e => {
          falhas.push(f.name);
          if (e.status === 0) this.erro.set('O backend não respondeu. Ele está rodando em localhost:8000?');
          proximo(i + 1);
        }
      });
    };
    proximo(0);
  }

  salvarArea(m: Material, ev: Event) {
    const area = (ev.target as HTMLInputElement).value.trim();
    if (!area || area === m.area) return;
    this.api.definirArea(m.id, area).subscribe(atual =>
      this.materiais.update(ms => ms.map(x => (x.id === atual.id ? atual : x))));
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
