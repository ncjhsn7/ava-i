import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <div class="logo"><span class="pulso"></span>AVA-I</div>
      <nav>
        <a routerLink="/docente" routerLinkActive="ativo">Docente</a>
        <a routerLink="/estudante" routerLinkActive="ativo">Sessão de estudo</a>
        <a routerLink="/dashboard" routerLinkActive="ativo">Dashboard</a>
      </nav>
    </header>
    <router-outlet />
  `,
  styles: `
    header{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--linha);padding:0 28px;display:flex;align-items:center;height:58px}
    .logo{font-weight:700;font-size:17px;display:flex;align-items:center;gap:9px}
    .pulso{width:10px;height:10px;border-radius:50%;background:var(--verde);box-shadow:0 0 0 3px var(--verde-claro)}
    nav{display:flex;gap:4px;margin-left:auto}
    nav a{padding:8px 16px;border-radius:8px;color:var(--ink-soft);font-weight:600;font-size:14px;text-decoration:none}
    nav a.ativo{background:var(--verde-claro);color:var(--verde)}
  `
})
export class AppComponent {}
