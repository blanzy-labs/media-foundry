class_name ScrappyMediaSlot
extends RefCounted

## Deterministic geometry and playback policy for the canonical MF-003 media slot.

func frame_index(elapsed: float, frame_rate: int, available_frames: int, requested_frames: int) -> int:
	return mini(int(floor(maxf(0.0, elapsed) * float(frame_rate))), mini(available_frames, requested_frames) - 1)

func geometry(source_size: Vector2, safe: Rect2, fit: String, anchor: String, motion: String, progress: float, slow_push_amount: float, gentle_pan_amount: float) -> Dictionary:
	var source := Rect2(Vector2.ZERO, source_size)
	var destination := safe
	if fit == "contain":
		var scale_value: float = minf(safe.size.x / source_size.x, safe.size.y / source_size.y)
		var size: Vector2 = source_size * scale_value
		if motion == "slow_push":
			size *= 1.0 - slow_push_amount * (1.0 - progress)
		var position: Vector2 = safe.get_center() - size / 2.0
		if anchor == "top": position.y = safe.position.y
		elif anchor == "bottom": position.y = safe.end.y - size.y
		elif anchor == "left": position.x = safe.position.x
		elif anchor == "right": position.x = safe.end.x - size.x
		if motion == "gentle_pan":
			var travel: float = maxf(0.0, safe.size.x - size.x) * gentle_pan_amount
			position.x += lerpf(-travel, travel, progress)
			position.x = clampf(position.x, safe.position.x, safe.end.x - size.x)
		destination = Rect2(position, size)
	else:
		var scale_value: float = maxf(safe.size.x / source_size.x, safe.size.y / source_size.y)
		var view_size: Vector2 = safe.size / scale_value
		if motion == "slow_push":
			view_size *= 1.0 - slow_push_amount * progress
		var source_position: Vector2 = (source_size - view_size) / 2.0
		if anchor == "top": source_position.y = 0.0
		elif anchor == "bottom": source_position.y = source_size.y - view_size.y
		elif anchor == "left": source_position.x = 0.0
		elif anchor == "right": source_position.x = source_size.x - view_size.x
		if motion == "gentle_pan":
			var available: float = source_size.x - view_size.x
			source_position.x = clampf(source_position.x + lerpf(-available, available, progress) * gentle_pan_amount, 0.0, available)
		source = Rect2(source_position, view_size)
	return {"destination": destination, "source": source}
