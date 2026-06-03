from src.blackfen.content import lint_world


def test_world_content_refs_are_valid() -> None:
    world = lint_world()
    assert "blackfen_village" in world.locations
    assert world.locations["blackfen_village"].npcs
