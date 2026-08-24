extends RefCounted

const SUPPORTED_TYPES := ["intro", "statement", "media", "emphasis", "reveal", "outro"]
const SUPPORTED_TRANSITIONS := ["cut", "scrappy_pop", "slide"]

func build(fixture: Dictionary, grammar: Dictionary) -> Dictionary:
	if not fixture.has("beats"):
		return {"mode": "legacy", "duration": float(fixture.format.duration_seconds), "beats": []}
	var source = fixture.get("beats")
	if typeof(source) != TYPE_ARRAY or source.is_empty():
		return _failure("beats must be a non-empty array")
	var configured_duration := float(fixture.format.get("duration_seconds", 0))
	var limits: Dictionary = grammar.get("beats", {}).get("duration_seconds", {})
	var extended := str(fixture.get("visual_strategy", {}).get("preference", "")) in ["godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement"]
	var maximum := 30.0 if extended else float(limits.get("maximum", 20.0))
	if configured_duration < float(limits.get("minimum", 10.0)) or configured_duration > maximum:
		return _failure("configured duration must be between 10 and %d seconds" % int(maximum))
	var timeline := []
	var cursor := 0.0
	var ids := {}
	for index in range(source.size()):
		if typeof(source[index]) != TYPE_DICTIONARY:
			return _failure("beat %d must be an object" % index)
		var beat: Dictionary = source[index].duplicate(true)
		var beat_type := str(beat.get("type", ""))
		var duration := float(beat.get("duration", 0))
		var transition := str(beat.get("transition", "cut"))
		var beat_id := str(beat.get("id", "%s-%02d" % [beat_type, index + 1]))
		if beat_type not in SUPPORTED_TYPES:
			return _failure("unsupported beat type at index %d" % index)
		if duration <= 0.0:
			return _failure("beat %s duration must be positive" % beat_id)
		if transition not in SUPPORTED_TRANSITIONS:
			return _failure("unsupported transition on beat %s" % beat_id)
		if ids.has(beat_id):
			return _failure("duplicate beat id %s" % beat_id)
		if beat.has("start") or beat.has("end"):
			return _failure("explicit timing is not supported; use sequential durations")
		ids[beat_id] = true
		beat.id = beat_id
		beat.index = index
		beat.start = snappedf(cursor, 0.000001)
		beat.end = snappedf(cursor + duration, 0.000001)
		timeline.append(beat)
		cursor = float(beat.end)
	if absf(cursor - configured_duration) > 0.001:
		return _failure("beat durations must equal configured video duration")
	return {"status": "PASS", "mode": "beats", "duration": configured_duration, "beats": timeline}

func active_at(t: float, timeline: Dictionary) -> Dictionary:
	for beat in timeline.get("beats", []):
		if t >= float(beat.start) and t < float(beat.end):
			return beat
	if not timeline.get("beats", []).is_empty() and is_equal_approx(t, float(timeline.duration)):
		return timeline.beats[-1]
	return {}

func lifecycle(t: float, beat: Dictionary, grammar: Dictionary) -> Dictionary:
	var local := t - float(beat.start)
	var duration := float(beat.duration)
	var enter_seconds := minf(float(grammar.motion.ENTER.seconds), duration * 0.25)
	var exit_seconds := minf(float(grammar.motion.EXIT.seconds), duration * 0.2)
	var enter := clampf(local / maxf(enter_seconds, 0.001), 0.0, 1.0)
	var exit := clampf((local - (duration - exit_seconds)) / maxf(exit_seconds, 0.001), 0.0, 1.0)
	return {"local": local, "progress": clampf(local / duration, 0.0, 1.0), "enter": enter, "active": 1.0 - exit, "exit": exit}

func _failure(reason: String) -> Dictionary:
	return {"status": "FAIL", "reason": reason, "mode": "beats", "duration": 0.0, "beats": []}
