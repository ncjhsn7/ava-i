import { Component, OnInit, inject, signal } from '@angular/core';
import { ApiService, Cadeira, Painel } from '../services/api.service';

@Component({
  selector: 'app-painel',
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
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
