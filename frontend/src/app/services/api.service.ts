import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface Material {
  id: number;
  titulo: string;
  cenario: string;
  status: string;
}

export interface Questao {
  id: number;
  ordem: number;
  pergunta: string;
  opcoes: string[];
  correta: number;
  justificativa: string;
  chunk_fonte: string;
  status: string;
}

export interface TelemetriaItem {
  t_offset: number;
  focus: number;
  phone_eventos: number;
  modo: string;
}

export interface DadosDashboard {
  kpis: { sessoes: number; focus_medio: number; eventos_controle: number; eventos_intervencao: number };
  engajamento: { minutos: number[]; controle: (number | null)[]; intervencao: (number | null)[] };
  acertos_por_questao: { questao: string; acerto: number | null }[];
  pontos: { focus: number; acerto: number }[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  criarMaterial(titulo: string, cenario: string, arquivo: File) {
    const form = new FormData();
    form.append('titulo', titulo);
    form.append('cenario', cenario);
    form.append('arquivo', arquivo);
    return this.http.post<Material>(`${this.base}/materiais`, form);
  }

  listarMateriais(status?: string) {
    const sufixo = status ? `?status=${status}` : '';
    return this.http.get<Material[]>(`${this.base}/materiais${sufixo}`);
  }

  listarQuestoes(materialId: number, status?: string) {
    const sufixo = status ? `?status=${status}` : '';
    return this.http.get<Questao[]>(`${this.base}/materiais/${materialId}/questoes${sufixo}`);
  }

  atualizarQuestao(id: number, dados: Partial<Questao>) {
    return this.http.patch<Questao>(`${this.base}/questoes/${id}`, dados);
  }

  publicar(materialId: number) {
    return this.http.post<Material>(`${this.base}/materiais/${materialId}/publicar`, {});
  }

  iniciarSessao(materialId: number, condicao: string, modo: string) {
    return this.http.post<{ id: number }>(`${this.base}/sessoes`, { material_id: materialId, condicao, modo });
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

  dashboard(materialId: number) {
    return this.http.get<DadosDashboard>(`${this.base}/dashboard/${materialId}`);
  }
}
