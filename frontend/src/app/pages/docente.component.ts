import { Component, OnInit, inject, signal } from '@angular/core';
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
  nomeArquivo = signal('');
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
    this.nomeArquivo.set(this.arquivo?.name ?? '');
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
        this.nomeArquivo.set('');
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
