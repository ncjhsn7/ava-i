import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home.component';
import { ProfessorComponent } from './pages/docente.component';
import { EstudanteComponent } from './pages/estudante.component';
import { PainelComponent } from './pages/dashboard.component';

export const routes: Routes = [
  { path: '', component: HomeComponent, pathMatch: 'full' },
  { path: 'estudar', component: EstudanteComponent },
  { path: 'materiais', component: ProfessorComponent },
  { path: 'painel', component: PainelComponent },
  { path: '**', redirectTo: '' }
];
