import inspect
import analysis


def test_ranking_accuracy_signature_has_no_carga():
    params = list(inspect.signature(analysis.compute_ranking_accuracy).parameters)
    assert "carga" not in params and "ug307" not in params
    assert "ramos_inscritos" in params
