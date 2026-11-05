import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { corCadeira, inicial } from '../cores';
import { ApiService, Cadeira, Painel } from '../services/api.service';

@Component({
  selector: 'app-painel',
  imports: [RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class PainelComponent implements OnInit {
  api = inject(ApiService);
  private route = inject(ActivatedRoute);

  cadeiras = signal<Cadeira[]>([]);
  cadeiraId = signal(0);
  dados = signal<Painel | null>(null);

  ngOnInit() {
    this.api.listarCadeiras().subscribe(cs => this.cadeiras.set(cs));
    const id = Number(this.route.snapshot.queryParamMap.get('cadeira'));
    if (id) this.selecionar(id);
  }

  inicial = inicial;
  corCadeira = corCadeira;

  nomeCadeira() {
    return this.cadeiras().find(c => c.id === this.cadeiraId())?.nome ?? '';
  }

  selecionar(id: number) {
    this.cadeiraId.set(id);
    this.dados.set(null);
    if (id) this.api.painel(id).subscribe(d => this.dados.set(d));
  }
}
