import scoring


def test_schedule_filter_only_for_attendance_types():
    # tipo que exige asistencia + conflicto => NO pasa
    assert scoring.schedule_filter_passes("de Catedra", True) is False
    # tipo que exige asistencia + sin conflicto => pasa
    assert scoring.schedule_filter_passes("de Catedra", False) is True
    # tipo sin asistencia + conflicto => igual pasa
    assert scoring.schedule_filter_passes("Corrector", True) is True
    assert scoring.schedule_filter_passes("Coordinador Tipo 1", True) is True
