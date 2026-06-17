import { Injectable, signal } from '@angular/core';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

const OLHO_DIREITO = [33, 160, 158, 133, 153, 144];
const OLHO_ESQUERDO = [362, 385, 387, 263, 373, 380];
const WASM_CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm';
const MODELO = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';
const TOL_YAW = 0.13;
const TOL_PITCH = 0.10;
const GRACA_MS = 2500;
const JANELA_MS = 8000;

function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function ear(lm: { x: number; y: number }[], idx: number[]) {
  const p = idx.map(i => lm[i]);
  return (dist(p[1], p[5]) + dist(p[2], p[4])) / (2 * dist(p[0], p[3]));
}

function mediana(xs: number[]) {
  if (!xs.length) return 0;
  const o = [...xs].sort((a, b) => a - b);
  return o[Math.floor(o.length / 2)];
}

@Injectable({ providedIn: 'root' })
export class VisionService {
  foco = signal(0);
  earAtual = signal<number | null>(null);
  temRosto = signal(false);
  olhandoTela = signal(true);
  ativo = signal(false);
  calibrado = signal(false);
  erro = signal<string | null>(null);

  private landmarker?: FaceLandmarker;
  private stream?: MediaStream;
  private video?: HTMLVideoElement;
  private rodando = false;
  private limiar: number | null = null;
  private yawBase = 0.5;
  private pitchBase = 0.5;
  private calEar: number[] = [];
  private calYaw: number[] = [];
  private calPitch: number[] = [];
  private inicioCalibracao = 0;
  private inicioDistracao = 0;
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
      this.limiar = null;
      this.calEar = [];
      this.calYaw = [];
      this.calPitch = [];
      this.janela = [];
      this.inicioDistracao = 0;
      this.calibrado.set(false);
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
    let okRaw = false;
    if (res.faceLandmarks && res.faceLandmarks.length) {
      const lm = res.faceLandmarks[0];
      const valor = (ear(lm, OLHO_DIREITO) + ear(lm, OLHO_ESQUERDO)) / 2;
      this.earAtual.set(Number(valor.toFixed(3)));
      this.temRosto.set(true);
      const olhoY = (lm[33].y + lm[263].y) / 2;
      const alturaRosto = Math.max(0.02, lm[152].y - olhoY);
      const pitch = (lm[1].y - olhoY) / alturaRosto;
      const largura = Math.max(0.02, lm[454].x - lm[234].x);
      const yaw = (lm[1].x - lm[234].x) / largura;
      if (this.limiar === null) {
        if (agora - this.inicioCalibracao < 5000) {
          this.calEar.push(valor);
          this.calYaw.push(yaw);
          this.calPitch.push(pitch);
        } else {
          this.limiar = 0.72 * (mediana(this.calEar) || 0.25);
          this.yawBase = mediana(this.calYaw);
          this.pitchBase = mediana(this.calPitch);
          this.calibrado.set(true);
        }
        okRaw = true;
      } else {
        const olhosAbertos = valor > this.limiar;
        const naTela = Math.abs(yaw - this.yawBase) < TOL_YAW && Math.abs(pitch - this.pitchBase) < TOL_PITCH;
        this.olhandoTela.set(naTela);
        okRaw = olhosAbertos && naTela;
      }
    } else {
      this.temRosto.set(false);
      this.earAtual.set(null);
      this.olhandoTela.set(false);
    }
    let ok: boolean;
    if (okRaw) {
      this.inicioDistracao = 0;
      ok = true;
    } else {
      if (this.inicioDistracao === 0) this.inicioDistracao = agora;
      ok = (agora - this.inicioDistracao) < GRACA_MS;
    }
    this.janela.push({ t: agora, ok });
    while (this.janela.length && agora - this.janela[0].t > JANELA_MS) this.janela.shift();
    const positivas = this.janela.filter(a => a.ok).length;
    this.foco.set(Math.round((100 * positivas) / Math.max(1, this.janela.length)));
    requestAnimationFrame(() => this.loop());
  }
}
