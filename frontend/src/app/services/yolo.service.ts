import { Injectable, signal } from '@angular/core';
import * as ort from 'onnxruntime-web';

const MODELO_LOCAL = '/assets/yolov8n.onnx';
const CLASSE_CELULAR = 67;
const LIMIAR_SCORE = 0.35;
const QUADROS_CONSECUTIVOS = 2;
const TAMANHO = 640;

@Injectable({ providedIn: 'root' })
export class YoloService {
  disponivel = signal(false);
  eventos = signal(0);
  celularVisivel = signal(false);
  confianca = signal(0);
  erro = signal<string | null>(null);

  private sessao?: ort.InferenceSession;
  private nomeSaida = 'output0';
  private nomeEntrada = 'images';
  private video?: HTMLVideoElement;
  private canvas = document.createElement('canvas');
  private rodando = false;
  private consecutivos = 0;
  private emEvento = false;

  async iniciar(video: HTMLVideoElement): Promise<boolean> {
    try {
      ort.env.wasm.wasmPaths = '/onnx/';
      ort.env.wasm.numThreads = 1;
      const resposta = await fetch(MODELO_LOCAL, { method: 'HEAD' });
      if (!resposta.ok) {
        this.erro.set('Modelo yolov8n.onnx não encontrado em /assets.');
        return false;
      }
      this.sessao = await ort.InferenceSession.create(MODELO_LOCAL, { executionProviders: ['wasm'] });
      this.nomeEntrada = this.sessao.inputNames[0] ?? 'images';
      this.nomeSaida = this.sessao.outputNames[0] ?? 'output0';
      this.video = video;
      this.canvas.width = TAMANHO;
      this.canvas.height = TAMANHO;
      this.rodando = true;
      this.disponivel.set(true);
      this.erro.set(null);
      this.agendar();
      return true;
    } catch (e) {
      console.error('Detector de celular (YOLO) falhou ao iniciar:', e);
      this.erro.set('Detector de celular falhou ao carregar: ' + ((e as Error)?.message ?? e));
      this.disponivel.set(false);
      return false;
    }
  }

  parar() {
    this.rodando = false;
    this.disponivel.set(false);
    this.celularVisivel.set(false);
  }

  private agendar() {
    if (!this.rodando) return;
    setTimeout(() => this.inferir().catch(e => console.error('YOLO inferência:', e)).finally(() => this.agendar()), 1200);
  }

  private async inferir() {
    if (!this.sessao || !this.video || this.video.readyState < 2) return;
    const ctx = this.canvas.getContext('2d')!;
    ctx.fillStyle = '#777';
    ctx.fillRect(0, 0, TAMANHO, TAMANHO);
    const razao = Math.min(TAMANHO / this.video.videoWidth, TAMANHO / this.video.videoHeight);
    const largura = this.video.videoWidth * razao;
    const altura = this.video.videoHeight * razao;
    ctx.drawImage(this.video, (TAMANHO - largura) / 2, (TAMANHO - altura) / 2, largura, altura);
    const pixels = ctx.getImageData(0, 0, TAMANHO, TAMANHO).data;
    const entrada = new Float32Array(3 * TAMANHO * TAMANHO);
    const area = TAMANHO * TAMANHO;
    for (let i = 0; i < area; i++) {
      entrada[i] = pixels[i * 4] / 255;
      entrada[area + i] = pixels[i * 4 + 1] / 255;
      entrada[2 * area + i] = pixels[i * 4 + 2] / 255;
    }
    const tensor = new ort.Tensor('float32', entrada, [1, 3, TAMANHO, TAMANHO]);
    const saida = await this.sessao.run({ [this.nomeEntrada]: tensor });
    const dados = saida[this.nomeSaida].data as Float32Array;
    const colunas = 8400;
    const linhaCelular = (4 + CLASSE_CELULAR) * colunas;
    let melhor = 0;
    for (let i = 0; i < colunas; i++) {
      const s = dados[linhaCelular + i];
      if (s > melhor) melhor = s;
    }
    this.confianca.set(Math.round(melhor * 100));
    const detectado = melhor > LIMIAR_SCORE;
    this.celularVisivel.set(detectado);
    if (detectado) {
      this.consecutivos++;
      if (this.consecutivos >= QUADROS_CONSECUTIVOS && !this.emEvento) {
        this.eventos.update(n => n + 1);
        this.emEvento = true;
      }
    } else {
      this.consecutivos = 0;
      this.emEvento = false;
    }
  }
}
