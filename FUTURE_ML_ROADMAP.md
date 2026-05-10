# Future ML Roadmap

This file is a rough backlog for a future machine-learning upgrade. The current app should keep using OCR-first extraction, but these notes describe how to evolve it later.

## Goal
- Learn from user feedback on slicer screenshots.
- Improve which OCR regions and lines are selected for time and filament.
- Reduce manual heuristic tuning over time.

## Planned Workflow
1. User pastes a screenshot.
2. Current extractor produces a prediction.
3. App asks for confirmation: good, bad, or corrected values.
4. Save the screenshot plus labels as training data.
5. Retrain periodically on the accumulated examples.
6. Re-run the model on a validation set to see whether it improved.

## Likely Model Shape
- Keep OCR as the first stage.
- Train a small classifier or ranking model to choose among OCR lines/boxes.
- Optional later step: train a detector to identify fields on BambuStudio and IdeaMaker layouts.

## Data To Collect
- Screenshot image.
- Slicer type.
- Ground-truth time and filament.
- Notes about what was wrong: model time vs total time, grams vs meters, missing decimal, `g` read as `9`, `1` vs `7`.

## Success Criteria
- Better selection of total time over model printing time.
- Better filament selection in BambuStudio tables.
- Fewer false positives from OCR glyph mistakes.
- Confidence that tracks reality, not just OCR certainty.

## Integration Idea
- Keep the current GUI.
- Add a review button for each result.
- Store labeled examples in a local JSONL or SQLite file.
- Add an offline training command that builds a new model from the saved examples.
- Use the trained model as a scoring layer before the current heuristics.
