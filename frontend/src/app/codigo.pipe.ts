import { Pipe, PipeTransform } from '@angular/core';

/** Escapa o texto e transforma trechos entre crases (`assim`) em <code>. */
@Pipe({ name: 'codigo' })
export class CodigoPipe implements PipeTransform {
  transform(texto: string | null | undefined): string {
    const seguro = (texto ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return seguro.replace(/`([^`]+)`/g, '<code>$1</code>');
  }
}
