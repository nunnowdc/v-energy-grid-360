"""Organização das opções compartilhadas do Portal."""

from app.repositories.filters import FiltersRepository


def get_filter_options(repository: FiltersRepository) -> dict[str, object]:
    """Agrupa relações cadastrais sem transformar valores da Gold."""
    bairros_por_municipio: dict[str, set[str]] = {}
    for municipio, bairro in repository.get_municipio_bairro_pairs():
        bairros = bairros_por_municipio.setdefault(municipio, set())
        if bairro is not None:
            bairros.add(bairro)

    municipios_por_alimentador: dict[str, set[str]] = {}
    for alimentador, municipio in repository.get_alimentador_municipio_pairs():
        municipios_por_alimentador.setdefault(alimentador, set()).add(municipio)

    return {
        "competencias": sorted(set(repository.get_competencias())),
        "municipios": [
            {"nome": nome, "bairros": sorted(bairros)}
            for nome, bairros in sorted(bairros_por_municipio.items())
        ],
        "classes": sorted(set(repository.get_classes())),
        "alimentadores": [
            {
                "codigo": codigo,
                "municipios": sorted(municipios_por_alimentador.get(codigo, set())),
            }
            for codigo in sorted(set(repository.get_alimentadores()))
        ],
        "causas": sorted(set(repository.get_causas())),
    }
