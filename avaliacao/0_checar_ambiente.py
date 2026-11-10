"""Passo 0: confere se tudo que a coleta usa está funcionando, com uma chamada curta a cada modelo."""
import sys

import comum
import config

TESTE = 'Responda SOMENTE com o JSON {"ok": true}'


def checar(nome: str, cfg: dict) -> bool:
    try:
        r = comum.chamar(cfg, TESTE)
        comum.extrair_json(r["texto"])
        print(f"  OK   {nome:<22} {r['modelo_exato']:<26} {r['latencia_s']:.1f} s")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  FALHA {nome:<21} {cfg['modelo']:<22} {e}")
        return False


def main() -> int:
    print("PDFs no Âncora (id, fragmentos úteis, disciplina em config.MATERIAIS):")
    faltam = False
    try:
        app = comum.backend()
        titulos = comum.titulos_materiais()
        grupo_de = {mid: rot for rot, ids in config.MATERIAIS.items() for mid in ids}
        contagem = {}
        for mid, titulo in sorted(titulos.items()):
            n = len(app["rag"].bons_chunks(app["rag"].obter_chunks(mid)))
            contagem[mid] = n
            print(f"  {grupo_de.get(mid, '--'):>3}  id {mid:>3}  {n:>4}  {titulo}")
        for mid in grupo_de:
            if mid not in titulos:
                print(f"  id {mid} de config.MATERIAIS não existe no Âncora!")
                faltam = True
        fixos = sum(contagem.get(m, 0) for rot, ids in config.MATERIAIS.items() if rot != config.COMPLETAR for m in ids)
        disp = sum(contagem.get(m, 0) for m in config.MATERIAIS[config.COMPLETAR])
        precisa = config.TOTAL_FRAGMENTOS - fixos
        print("\nFragmentos na coleta: " + ", ".join(
            f"{rot} {sum(contagem.get(m, 0) for m in ids) if rot != config.COMPLETAR else max(0, precisa)}"
            for rot, ids in config.MATERIAIS.items()) + f" = {config.TOTAL_FRAGMENTOS}")
        if precisa > disp:
            print(f"  {config.COMPLETAR} tem só {disp} fragmentos úteis, mas precisa de {precisa}!")
            faltam = True
    except Exception as e:  # noqa: BLE001
        print(f"  FALHA ao ler o backend: {e}")
        return 1
    print("Modelos:")
    ok = all([checar(n, c) for n, c in config.GERADORES.items()]
             + [checar("tema", config.MODELO_TEMA), checar("JUIZ", config.JUIZ)])
    if faltam:
        print("\nAjuste config.MATERIAIS: não há fragmentos úteis suficientes. A coleta NÃO foi iniciada.")
    print("\nTudo certo para a coleta." if ok and not faltam else "\nCorrija os problemas acima antes de seguir.")
    return 0 if ok and not faltam else 1


if __name__ == "__main__":
    sys.exit(main())
