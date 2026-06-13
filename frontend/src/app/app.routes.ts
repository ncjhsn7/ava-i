import { Routes } from '@angular/router';
import { DocenteComponent } from './pages/docente.component';
import { EstudanteComponent } from './pages/estudante.component';
import { DashboardComponent } from './pages/dashboard.component';

export const routes: Routes = [
  { path: 'docente', component: DocenteComponent },
  { path: 'estudante', component: EstudanteComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: '', pathMatch: 'full', redirectTo: 'docente' }
];
