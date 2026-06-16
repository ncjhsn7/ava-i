import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface Cadeira {
  id: number;
  nome: string;
}

export interface Material {
  id: number;
  cadeira_id: number;
  titulo: string;
  status: string;
}

export interface Questao {
  id: number;
  ordem: number;
  topico: string;
  pergunta: string;
  opcoes: string[];
  correta: number;
  justificativa: string;
  chunk_fonte: string;
  status: string;
}

export interface Pergunta {
  pergunta: string;
  opcoes: string[];
  correta: number;
  justificativa: string;
  fonte: string;
}

export interface TelemetriaItem {
  t_offset: number;
  focus: number;
  phone_eventos: number;
  modo: string;
}

export interface Painel {
  kpis: {
    sessoes: number;
    respostas: number;
    acerto_medio: number;
    foco_medio: number | null;
    tempo_estudo_min: number;
    tempo_focado_min: number;
    eventos_celular: number;
  };
  foco_no_tempo: { minutos: number[]; foco: number[] };
  acertos_por_topico: { topico: string; acerto: number | null; respostas: number }[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  listarCadeiras() {
    return this.http.get<Cadeira[]>(`${this.base}/cadeiras`);
  }

  criarCadeira(nome: string) {
    return this.http.post<Cadeira>(`${this.base}/cadeiras`, { nome });
  }

  removerCadeira(cadeiraId: number) {
    return this.http.delete(`${this.base}/cadeiras/${cadeiraId}`);
  }

  listarMateriais(cadeiraId: number) {
    return this.http.get<Material[]>(`${this.base}/cadeiras/${cadeiraId}/materiais`);
  }

  criarMaterial(cadeiraId: number, titulo: string, arquivo: File) {
    const form = new FormData();
    form.append('titulo', titulo);
    form.append('arquivo', arquivo);
    return this.http.post<Material>(`${this.base}/cadeiras/${cadeiraId}/materiais`, form);
  }

  removerMaterial(materialId: number) {
    return this.http.delete(`${this.base}/materiais/${materialId}`);
  }

  previewMaterial(materialId: number) {
    return this.http.post<Pergunta>(`${this.base}/materiais/${materialId}/preview`, {});
  }

  iniciarSessao(cadeiraId: number, modo: string, materialIds: number[]) {
    return this.http.post<{ sessao_id: number }>(`${this.base}/sessoes`, { cadeira_id: cadeiraId, modo, material_ids: materialIds });
  }

  proximaQuestao(sessaoId: number, materialIds: number[]) {
    return this.http.post<Questao>(`${this.base}/sessoes/${sessaoId}/questao`, { material_ids: materialIds });
  }

  gerarEstudo(cadeiraId: number, materialIds: number[], nivel: string, objetivo: string, tempo: string) {
    return this.http.post<{ texto: string }>(`${this.base}/cadeiras/${cadeiraId}/estudo`, {
      material_ids: materialIds, nivel, objetivo, tempo
    });
  }

  enviarTelemetria(sessaoId: number, itens: TelemetriaItem[]) {
    return this.http.post(`${this.base}/sessoes/${sessaoId}/telemetria`, { itens });
  }

  responder(sessaoId: number, questaoId: number, escolhida: number) {
    return this.http.post<{ acertou: boolean; correta: number; justificativa: string }>(
      `${this.base}/sessoes/${sessaoId}/respostas`, { questao_id: questaoId, escolhida });
  }

  encerrarSessao(sessaoId: number) {
    return this.http.post(`${this.base}/sessoes/${sessaoId}/encerrar`, {});
  }

  painel(cadeiraId: number) {
    return this.http.get<Painel>(`${this.base}/cadeiras/${cadeiraId}/dashboard`);
  }
}
