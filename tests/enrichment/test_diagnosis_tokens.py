from src.enrichment.diagnosis_tokens import build_diagnosis_specs, tokenize_diagnosis


def test_tokenize_long_mimic_style_diagnosis():
    tokens = tokenize_diagnosis("Diabetes with peripheral circulatory disorders")
    assert "diabetes" in tokens
    assert "peripheral" in tokens
    assert "with" not in tokens


def test_tokenize_short_phrase():
    assert tokenize_diagnosis("heart failure") == ["heart", "failure"]


def test_build_diagnosis_specs_preserves_input_dx():
    specs = build_diagnosis_specs(["Heart Failure", ""])
    assert len(specs) == 1
    assert specs[0]["input_dx"] == "Heart Failure"
    assert "heart" in specs[0]["tokens"]
    assert "failure" in specs[0]["tokens"]
