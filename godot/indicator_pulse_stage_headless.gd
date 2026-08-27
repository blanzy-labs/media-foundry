extends SceneTree

## Headless entry point for validating the scene-attached indicator stage.
## The runtime stage intentionally remains a Node2D and must not be passed to --script.

const IndicatorPulseStageScript = preload("res://indicator_pulse_stage.gd")
const ActivityVocabularyStageScript = preload("res://activity_vocabulary_stage.gd")

func _initialize() -> void:
	var indicator_stage = IndicatorPulseStageScript.new()
	var activity_stage = ActivityVocabularyStageScript.new()
	if not indicator_stage is Node2D or not activity_stage is Node2D:
		push_error("INDICATOR_PULSE_STAGE_HEADLESS_TYPE_FAILED")
		quit(1)
		return
	indicator_stage.free()
	activity_stage.free()
	print("INDICATOR_PULSE_STAGE_HEADLESS_OK runtime_base=Node2D direct_script_entry=false")
	quit(0)
