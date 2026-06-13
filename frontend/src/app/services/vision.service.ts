import { Injectable, signal } from '@angular/core';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

const OLHO_DIREITO = [33, 160, 158, 133, 153, 144];
const OLHO_ESQUERDO = [362, 385, 387, 263, 373, 380];
const WASM_CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
const MODELO = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function ear(lm: { x: number; y: number }[], idx: number[]) {
  const p = idx.map(i => lm[i]);
  return (dist(p[1], p[5]) + dist(p[2], p[4])) / (2 * dist(p[0], p[3]));
}

@Injectable({ providedIn: 'root' })
export class VisionService {
  foco = signal(0);
  earAtual = signal<number | null>(null);
  temRosto = signal(false);
  ativo = signal(false);
  calibrado = signal(false);
  erro = signal<string | null>(null);

  private landmarker?: FaceLandmarker;
  private stream?: MediaStream;
  private video?: HTMLVideoElement;
  private rodando = false;
  private limiar: number | null = null;
  private amostrasCalibracao: number[] = [];
  private inicioCalibracao = 0;
  private janela: { t: number; ok: boolean }[] = [];

  async iniciar(video: HTMLVideoElement): Promise<boolean> {
    try {
      const fileset = await FilesetResolver.forVisionTasks(WASM_CDN);
      this.landmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODELO },
        runningMode: 'VIDEO',
        numFaces: 1
      });
      this.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } });
      video.srcObject = this.stream;
      await video.play();
      this.video = video;
      this.rodando = true;
      this.ativo.set(true);
      this.inicioCalibracao = performance.now();
      requestAnimationFrame(() => this.loop());
      return true;
    } catch (e) {
      this.erro.set('Visão computacional indisponível neste ambiente — modo degradado.');
      this.ativo.set(false);
      return false;
    }
  }

  parar() {
    this.rodando = false;
    this.ativo.set(false);
    this.stream?.getTracks().forEach(t => t.stop());
  }

  private loop() {
    if (!this.rodando || !this.landmarker || !this.video) return;
    const agora = performance.now();
    const res = this.landmarker.detectForVideo(this.video, agora);
    let ok = false;
    if (res.faceLandmarks && res.faceLandmarks.length) {
      const lm = res.faceLandmarks[0];
      const valor = (ear(lm, OLHO_DIREITO) + ear(lm, OLHO_ESQUERDO)) / 2;
      this.earAtual.set(Number(valor.toFixed(3)));
      this.temRosto.set(true);
      const nariz = lm[1];
      const centrado = nariz.x > 0.2 && nariz.x < 0.8;
      if (this.limiar === null) {
        if (agora - this.inicioCalibracao < 5000) {
          this.amostrasCalibracao.push(valor);
        } else {
          const ordenadas = [...this.amostrasCalibracao].sort((a, b) => a - b);
          this.limiar = 0.72 * (ordenadas[Math.floor(ordenadas.length / 2)] ?? 0.25);
          this.calibrado.set(true);
        }
        ok = true;
      } else {
        ok = centrado && valor > this.limiar;
      }
    } else {
      this.temRosto.set(false);
      this.earAtual.set(null);
    }
    this.janela.push({ t: agora, ok });
    while (this.janela.length && agora - this.janela[0].t > 12000) this.janela.shift();
    const positivas = this.janela.filter(a => a.ok).length;
    this.foco.set(Math.round((100 * positivas) / Math.max(1, this.janela.length)));
    requestAnimationFrame(() => this.loop());
  }
}
