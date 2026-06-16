import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <nav>
        <a routerLink="/estudar" routerLinkActive="ativo">Estudar</a>
        <a routerLink="/professor" routerLinkActive="ativo">Professor</a>
        <a routerLink="/painel" routerLinkActive="ativo">Painel</a>
      </nav>
    </header>
    <router-outlet />
  `,
  styles: `
    header{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--linha);padding:0 24px;display:flex;align-items:center;height:52px}
    nav{display:flex;gap:2px}
    nav a{padding:7px 14px;border-radius:4px;color:var(--ink-soft);font-weight:600;font-size:13.5px}
    nav a:hover{color:var(--ink)}
    nav a.ativo{background:var(--accent-soft);color:var(--accent)}
  `
})
export class AppComponent {}
