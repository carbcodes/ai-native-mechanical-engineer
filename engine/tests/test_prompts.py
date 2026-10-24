from mechy.agents.cards import ROLES
from mechy.agents.providers import role_prompt


def test_every_role_gets_the_engineering_standards():
    for role in ROLES:
        prompt = role_prompt(role)
        assert "Mechy engineering standards" in prompt, role
        assert "verification table" in prompt, role


def test_planner_runs_prior_art_and_concepts_first():
    prompt = role_prompt("planner")
    assert "prior art" in prompt and "concept" in prompt


def test_concepts_present_the_conventional_design_first():
    assert "present it first" in role_prompt("concept")


def test_every_role_points_at_existing_reference_files():
    from mechy.agents.providers import ROLE_LIBRARY, KNOWLEDGE, DATA
    for role in ROLES:
        notes, sets = ROLE_LIBRARY[role]
        assert notes and all((KNOWLEDGE / f"{n}.md").exists() for n in notes), role
        assert all((DATA / s / "README.md").exists() for s in sets), role
        prompt = role_prompt(role)
        assert str(KNOWLEDGE / f"{notes[0]}.md") in prompt, role
        assert "value_type" in prompt, role


def test_cad_reads_standard_parts_and_controls_reads_electronics():
    assert "data/standard_parts" in role_prompt("cad")
    assert "knowledge/electronics.md" in role_prompt("controls")
