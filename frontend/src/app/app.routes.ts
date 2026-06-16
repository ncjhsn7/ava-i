import { Routes } from '@angular/router';
import { ProfessorComponent } from './pages/docente.component';
import { EstudanteComponent } from './pages/estudante.component';
import { PainelComponent } from './pages/dashboard.component';

export const routes: Routes = [
  { path: 'estudar', component: EstudanteComponent },
  { path: 'professor', component: ProfessorComponent },
  { path: 'painel', component: PainelComponent },
  { path: '', pathMatch: 'full', redirectTo: 'estudar' }
];
