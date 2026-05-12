"""One full game turn pipeline.

Design sources:
- 03-LLM-Architecture.md: The Handoff Point
- 05-Interaction-System.md: The Interaction Flow

Target flow:
validate action -> apply deterministic rules -> produce MechanicalResult ->
optionally narrate -> persist state and trace -> return next visible actions.
"""
