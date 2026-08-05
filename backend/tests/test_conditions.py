from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed.condition_seed import seed_conditions


def test_list_conditions_is_database_backed(client: TestClient, db_session: Session) -> None:
    seed_conditions(db_session)

    response = client.get("/api/conditions")
    assert response.status_code == 200
    conditions = response.json()

    assert len(conditions) == 79
    expected_fields = {
        "id", "name", "description", "type",
        "defaultIncubationRounds", "defaultDurationRounds",
        "defaultFrequencyRounds", "defaultSuccessesRequired",
    }
    assert all(expected_fields <= set(condition) for condition in conditions)

    veraengstigt = next(c for c in conditions if c["name"] == "Verängstigt")
    assert veraengstigt["type"] == "condition"
    assert "flieht vor der Quelle ihrer Furcht" in veraengstigt["description"]
    assert veraengstigt["defaultDurationRounds"] is None

    benommen = next(c for c in conditions if c["name"] == "Benommen")
    assert benommen["defaultDurationRounds"] == 1

    wyverngift = next(c for c in conditions if c["name"] == "Wyverngift")
    assert wyverngift["type"] == "poison"
    assert "SG: 17" in wyverngift["description"]
    assert wyverngift["defaultFrequencyRounds"] == 1
    assert wyverngift["defaultSuccessesRequired"] == 2

    arsen = next(c for c in conditions if c["name"] == "Arsen")
    assert arsen["defaultIncubationRounds"] == 100
    assert arsen["defaultFrequencyRounds"] == 10
    assert arsen["defaultSuccessesRequired"] == 1

    beulenpest = next(c for c in conditions if c["name"] == "Beulenpest")
    assert beulenpest["type"] == "disease"
    assert "Frequenz 1/ Tag" in beulenpest["description"]
    assert beulenpest["defaultIncubationRounds"] == 14400
    assert beulenpest["defaultFrequencyRounds"] == 14400
    assert beulenpest["defaultSuccessesRequired"] == 2

    # Lepra's incubation/frequency are dice-based ("2W4 Wochen") and in an
    # unsupported unit (weeks) respectively — both stay unparsed (None).
    lepra = next(c for c in conditions if c["name"] == "Lepra")
    assert lepra["defaultIncubationRounds"] is None
    assert lepra["defaultFrequencyRounds"] is None
    assert lepra["defaultSuccessesRequired"] == 2
