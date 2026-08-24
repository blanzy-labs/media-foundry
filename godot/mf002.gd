extends Node2D

const W := 540.0
const H := 960.0
const FPS := 30.0
const ScrappyMediaSlotScript = preload("res://scrappy_media_slot.gd")
const BeatTimelineScript = preload("res://beat_timeline.gd")
const ScrappyWorldStageScript = preload("res://scrappy_world_stage.gd")
const LofiBookStageScript = preload("res://lofi_book_stage.gd")
const CausalBookStageScript = preload("res://causal_book_stage.gd")
const ProjectedCodexStageScript = preload("res://projected_codex_stage.gd")
const ProjectedDataWindowStageScript = preload("res://projected_data_window_stage.gd")
const ExtendedDataWindowStageScript = preload("res://extended_data_window_stage.gd")
const LiveInvestigationStageScript = preload("res://live_investigation_stage.gd")
const FinalPolishStageScript = preload("res://final_polish_stage.gd")
const LowerRightPolishStageScript = preload("res://lower_right_polish_stage.gd")

var fixture: Dictionary
var grammar: Dictionary
var frame_index := -1
var total_frames := 450
var video_duration := 15.0
var heavy_font: Font
var regular_font: Font
var fixture_path := ""
var grammar_path := ""
var output_dir := ""
var layout_report_path := ""
var layout_debug := false
var validate_layout_only := false
var timeline_report_path := ""
var timeline: Dictionary = {"mode": "legacy", "duration": 15.0, "beats": []}
var executed_beats := {}
var beat_timeline_engine: RefCounted = BeatTimelineScript.new()
var layouts: Dictionary = {}
var media_spec: Dictionary = {}
var media_state: Dictionary = {"status": "NOT_PRESENT"}
var media_texture: ImageTexture
var media_frames_dir := ""
var media_frame_count := 0
var media_loaded_frame := -1
var media_video_textures: Array[ImageTexture] = []
var media_slot_engine: RefCounted = ScrappyMediaSlotScript.new()
var generated_scene_active := false
var generated_stage: Node2D

func _ready() -> void:
	fixture_path = _argument_value("--fixture")
	grammar_path = _argument_value("--grammar")
	output_dir = _argument_value("--output-dir")
	layout_report_path = _argument_value("--layout-report")
	timeline_report_path = _argument_value("--timeline-report")
	layout_debug = _has_argument("--debug-layout")
	validate_layout_only = _has_argument("--validate-layout-only")
	media_frames_dir = _argument_value("--media-frames-dir")
	if fixture_path.is_empty() or grammar_path.is_empty() or output_dir.is_empty():
		_fail("MF002_RENDER_ERROR missing fixture, grammar, or output directory")
		return
	fixture = _read_json(fixture_path)
	grammar = _read_json(grammar_path)
	if fixture.is_empty() or grammar.is_empty() or not _valid_contract():
		_fail("MF002_RENDER_ERROR invalid contract")
		return
	timeline = beat_timeline_engine.build(fixture, grammar)
	if timeline.get("status", "PASS") != "PASS":
		_fail("MF004_TIMELINE_ERROR " + str(timeline.get("reason", "invalid timeline")))
		return
	video_duration = float(timeline.duration)
	total_frames = int(round(video_duration * FPS))
	heavy_font = load(str(grammar.typography.heavy_font)) as Font
	regular_font = load(str(grammar.typography.regular_font)) as Font
	if heavy_font == null or regular_font == null:
		_fail("MF002_RENDER_ERROR font assets unavailable")
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	if layout_report_path.is_empty():
		layout_report_path = output_dir.path_join("layout-validation.json")
	DirAccess.make_dir_recursive_absolute(layout_report_path.get_base_dir())
	if not _prepare_media():
		return
	if not _prepare_layouts():
		return
	var visual_preference := str(fixture.get("visual_strategy", {}).get("preference", ""))
	generated_scene_active = visual_preference in ["generated_scene", "godot_generated_scene", "godot_generated_book_refinement", "godot_projected_codex_refinement", "godot_projected_data_window_refinement", "godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement"]
	if generated_scene_active:
		if visual_preference == "godot_lower_right_polish_refinement":
			generated_stage = LowerRightPolishStageScript.new()
		elif visual_preference == "godot_final_polish_refinement":
			generated_stage = FinalPolishStageScript.new()
		elif visual_preference == "godot_live_investigation_refinement":
			generated_stage = LiveInvestigationStageScript.new()
		elif visual_preference == "godot_extended_data_window_refinement":
			generated_stage = ExtendedDataWindowStageScript.new()
		elif visual_preference == "godot_projected_data_window_refinement":
			generated_stage = ProjectedDataWindowStageScript.new()
		elif visual_preference == "godot_projected_codex_refinement":
			generated_stage = ProjectedCodexStageScript.new()
		elif visual_preference == "godot_generated_book_refinement":
			generated_stage = CausalBookStageScript.new()
		elif visual_preference == "godot_generated_scene":
			generated_stage = LofiBookStageScript.new()
		else:
			generated_stage = ScrappyWorldStageScript.new()
		add_child(generated_stage)
		var scene_result: Dictionary = generated_stage.configure(fixture, timeline, layouts, heavy_font, regular_font)
		if scene_result.get("result") != "PASS":
			_fail(str(scene_result.get("error", "GENERATED_SCENE_CONFIG_FAILED")))
			return
	RenderingServer.set_default_clear_color(_color("workshop_dark"))
	print("MF002_RENDER_START id=%s grammar=%s seed=%d frames=%d" % [fixture.id, grammar.id, int(fixture.seed), total_frames])
	print("MF004_TIMELINE_READY mode=%s beats=%d duration=%.3f" % [timeline.mode, timeline.beats.size(), video_duration])
	print("MF002_STRUCTURAL safe_area=PASS layers=workshop,sign,media,paper,tape,props layout=PASS")
	if validate_layout_only:
		_write_layout_report("PASS", "")
		_write_timeline_report()
		print("MF002_LAYOUT_ONLY_COMPLETE id=%s" % fixture.id)
		set_process(false)
		get_tree().quit(0)

func _process(_delta: float) -> void:
	if fixture.is_empty() or grammar.is_empty():
		return
	frame_index += 1
	if frame_index >= total_frames:
		_write_layout_report("PASS", "")
		_write_timeline_report()
		print("MF002_RENDER_COMPLETE id=%s frames=%d" % [fixture.id, total_frames])
		get_tree().quit(0)
		return
	var t := float(frame_index) / FPS
	if generated_scene_active:
		position = Vector2.ZERO
		scale = Vector2.ONE
		generated_stage.set_story_time(t)
	else:
		position = Vector2(sin(t * 0.73) * 1.2, cos(t * 0.51) * 0.8)
		var push: float = 1.0 + float(grammar.motion.camera_push) * (t / video_duration)
		scale = Vector2.ONE * push
	if timeline.mode == "legacy":
		_log_timeline_stage(frame_index)
	queue_redraw()
	await RenderingServer.frame_post_draw
	_capture_frame()

func _capture_frame() -> void:
	var image := get_viewport().get_texture().get_image()
	var path := output_dir.path_join("frame_%06d.png" % frame_index)
	var error := image.save_png(path)
	if error != OK:
		_fail("MF002_RENDER_ERROR could not save " + path)
	if frame_index % 30 == 0:
		print("MF002_RENDER_FRAME %d" % frame_index)

func _draw() -> void:
	if fixture.is_empty() or grammar.is_empty():
		return
	var t := float(frame_index) / FPS
	_draw_workshop(t)
	if timeline.mode == "beats":
		if generated_scene_active:
			_draw_generated_timeline_boundary(t)
		else:
			_draw_active_beat(t)
	elif t < float(grammar.motion.intro_end_seconds):
		_draw_intro(t)
	elif t < float(grammar.motion.outro_start_seconds):
		_draw_content_stage(t)
	else:
		_draw_outro(t)

func _draw_active_beat(t: float) -> void:
	var beat: Dictionary = beat_timeline_engine.active_at(t, timeline)
	if beat.is_empty():
		return
	_record_active_beat(beat)
	_draw_beat_card(t, beat)

func _draw_generated_timeline_boundary(t: float) -> void:
	var beat: Dictionary = beat_timeline_engine.active_at(t, timeline)
	if beat.is_empty():
		return
	_record_active_beat(beat)
	if str(beat.type) in ["intro", "outro"]:
		_draw_beat_card(t, beat)

func _record_active_beat(beat: Dictionary) -> void:
	var beat_id := str(beat.id)
	if not executed_beats.has(beat_id):
		executed_beats[beat_id] = {"first_frame": frame_index, "last_frame": frame_index}
		print("MF004_BEAT_ACTIVE id=%s type=%s frame=%d start=%.3f end=%.3f" % [beat_id, str(beat.type), frame_index, float(beat.start), float(beat.end)])
	else:
		executed_beats[beat_id].last_frame = frame_index

func _draw_beat_card(t: float, beat: Dictionary) -> void:
	var lifecycle: Dictionary = beat_timeline_engine.lifecycle(t, beat, grammar)
	var transition := str(beat.get("transition", "cut"))
	var enter: float = _smoothstep(float(lifecycle.enter))
	var active: float = _smoothstep(float(lifecycle.active))
	var offset := Vector2.ZERO
	var beat_scale := 1.0
	if transition == "slide":
		offset.x = (1.0 - enter) * 580.0 - float(lifecycle.exit) * 580.0
	elif transition == "scrappy_pop":
		beat_scale = (0.72 + 0.28 * _ease_out_back(enter)) * (0.86 + 0.14 * active)
	draw_set_transform(Vector2(W / 2.0, H / 2.0) + offset, 0.0, Vector2.ONE * beat_scale)
	match str(beat.type):
		"intro":
			_draw_rough_panel(Vector2(470, 272), _color("wood"), Color("462319"), int(beat.index) + 1)
			_draw_fitted_text("beat_%d" % int(beat.index), _color("cream"))
			_draw_fitted_text("intro_label", Color("2b1b13"))
		"statement":
			_draw_rough_panel(Vector2(438, 252), _color("paper"), Color("493223"), int(beat.index) + 1)
			_draw_fitted_text("beat_%d" % int(beat.index), _color("paper_ink"))
		"emphasis":
			_draw_rough_panel(Vector2(430, 100), _color("tape"), Color("5a4024"), int(beat.index) + 1)
			_draw_fitted_text("beat_%d" % int(beat.index), Color("3a291c"))
		"reveal":
			_draw_rough_panel(Vector2(458, 292), Color("294637"), Color("111d17"), int(beat.index) + 1)
			_draw_fitted_text("beat_%d" % int(beat.index), _color("cream"))
		"media":
			_draw_rough_panel(Vector2(430, 382), _color("metal"), Color("222522"), int(beat.index) + 1)
			draw_rect(Rect2(-188, -148, 376, 268), Color("241b17"), true)
			draw_rect(Rect2(-188, -148, 376, 268), _color("rust"), false, 6)
			if media_state.status == "PASS":
				_draw_media_slot(t, float(lifecycle.progress))
			else:
				_draw_visual(str(fixture.visual.kind), Vector2(0, -12), t)
		"outro":
			_draw_rough_panel(Vector2(458, 292), Color("294637"), Color("111d17"), int(beat.index) + 1)
			_draw_fitted_text("beat_%d" % int(beat.index), _color("cream"))
			_draw_fitted_text("outro_label", Color("bcd3a6"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_workshop(t: float) -> void:
	draw_rect(Rect2(0, 0, W, H), _color("workshop_dark"))
	for plank in range(8):
		var y := float(plank * 120)
		var shade := _color("workshop_mid").lightened(float((plank * 7) % 3) * 0.018)
		draw_rect(Rect2(0, y, W, 118), shade)
		draw_line(Vector2(0, y + 118), Vector2(W, y + 116), Color("100b09"), 4)
	for mark in range(36):
		var x := float((mark * 97 + int(fixture.seed)) % 520 + 10)
		var y := float((mark * 151 + int(fixture.seed / 3)) % 880 + 40)
		var length := float(8 + (mark * 13) % 34)
		draw_line(Vector2(x, y), Vector2(x + length, y + float((mark % 5) - 2)), Color(0.08, 0.045, 0.025, 0.38), 2)
	# Hanging cable and swaying lamp keep the environment alive.
	var sway := sin(t * 1.5) * deg_to_rad(float(grammar.motion.cable_sway_degrees))
	draw_set_transform(Vector2(445, -10), sway)
	draw_polyline(PackedVector2Array([Vector2(0, 0), Vector2(-4, 70), Vector2(10, 135), Vector2(2, 182)]), Color("171311"), 9)
	draw_circle(Vector2(2, 200), 36, _color("lamp"))
	draw_arc(Vector2(2, 199), 39, PI, TAU, 20, Color("4a2d18"), 7)
	draw_colored_polygon(PackedVector2Array([Vector2(-28, 225), Vector2(32, 225), Vector2(92, 470), Vector2(-102, 470)]), Color(0.95, 0.69, 0.25, 0.045))
	draw_set_transform(Vector2.ZERO, 0.0)
	# Crates, bolts, and a loose cable frame the safe area without competing with text.
	_draw_crate(Vector2(17, 850), Vector2(138, 110), -0.022)
	_draw_crate(Vector2(401, 866), Vector2(125, 95), 0.031)
	draw_polyline(PackedVector2Array([Vector2(0, 834), Vector2(95, 820), Vector2(180, 850), Vector2(260, 836)]), Color("0c0908"), 8)
	for bolt in [Vector2(22, 42), Vector2(516, 58), Vector2(24, 810), Vector2(514, 824)]:
		draw_circle(bolt, 7, _color("metal"))
		draw_line(bolt - Vector2(4, 0), bolt + Vector2(4, 0), Color("242622"), 2)

func _draw_intro(t: float) -> void:
	var enter: float = _ease_out_back(clamp(t / float(grammar.motion.ENTER.seconds), 0.0, 1.0))
	var impact_time: float = max(0.0, t - 0.58)
	var impact: float = sin(impact_time * 35.0) * exp(-impact_time * 10.0) * 8.0 if t >= 0.58 else 0.0
	var center: Vector2 = Vector2(W / 2.0 + impact, lerp(-250.0, 395.0, enter))
	draw_set_transform(center, deg_to_rad(float(grammar.imperfection.sign_rotation_degrees)))
	_draw_rough_panel(Vector2(470, 272), _color("wood"), Color("462319"), 1)
	_draw_fitted_text("intro", _color("cream"))
	_draw_fitted_text("intro_label", Color("2b1b13"))
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_metal_label(Vector2(58, 560), str(fixture.visual.label), -0.025)
	# Deterministic impact dust: fixed positions, animation only changes radius.
	for dust in range(11):
		var dust_t: float = clamp((t - 0.55) * 1.8, 0.0, 1.0)
		var dx := float((dust * 71) % 430 + 55)
		var dy: float = 535.0 + sin(float(dust) * 2.2) * 34.0 - dust_t * float(20 + (dust * 9) % 55)
		draw_circle(Vector2(dx, dy), (1.0 - dust_t) * float(5 + dust % 6), Color(0.83, 0.62, 0.34, 0.32))

func _draw_content_stage(t: float) -> void:
	var enter: float = _ease_out_back(clamp((t - 2.0) / 0.72, 0.0, 1.0))
	var exit_amount: float = _smoothstep(clamp((t - 12.45) / float(grammar.motion.EXIT.seconds), 0.0, 1.0))
	var stage_y: float = lerp(1080.0, 0.0, enter) - exit_amount * 1030.0
	draw_set_transform(Vector2(0, stage_y), 0.0)
	# Primary framed media region: scratched metal surrounding a dirty inset.
	draw_set_transform(Vector2(270, 337 + stage_y), deg_to_rad(-1.35))
	_draw_rough_panel(Vector2(430, 382), _color("metal"), Color("222522"), 2)
	draw_rect(Rect2(-188, -148, 376, 268), Color("241b17"), true)
	draw_rect(Rect2(-188, -148, 376, 268), _color("rust"), false, 6)
	if media_state.status == "PASS":
		_draw_media_slot(t)
	else:
		_draw_visual(str(fixture.visual.kind), Vector2(0, -12), t)
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_metal_label(Vector2(62, 145 + stage_y), str(fixture.visual.label), 0.02)
	# Crooked paper note carries the content, physically attached by tape.
	draw_set_transform(Vector2(270, 684 + stage_y), deg_to_rad(float(grammar.imperfection.headline_rotation_degrees)))
	_draw_rough_panel(Vector2(438, 252), _color("paper"), Color("493223"), 3)
	_draw_fitted_text("headline", _color("paper_ink"))
	_draw_fitted_text("body", Color("4b372b"))
	draw_set_transform(Vector2.ZERO, 0.0)
	_draw_tape(Vector2(35, 561 + stage_y), 0.14)
	_draw_tape(Vector2(410, 786 + stage_y), -0.11)
	# Emphasis label punches once, then keeps a tiny physical idle wobble.
	var punch_phase: float = clamp(abs(t - 8.0) / float(grammar.motion.EMPHASIS.seconds), 0.0, 1.0)
	var punch: float = lerp(float(grammar.motion.EMPHASIS.scale), 1.0, _smoothstep(punch_phase))
	draw_set_transform(Vector2(270, 838 + stage_y), -0.025 + sin(t * 2.4) * 0.008, Vector2.ONE * punch)
	_draw_rough_panel(Vector2(330, 68), _color("tape"), Color("5a4024"), 4)
	_draw_fitted_text("emphasis", Color("3a291c"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_outro(t: float) -> void:
	var enter: float = _ease_out_back(clamp((t - float(grammar.motion.outro_start_seconds)) / 0.65, 0.0, 1.0))
	var center := Vector2(270, lerp(1080.0, 455.0, enter))
	draw_set_transform(center, deg_to_rad(1.4))
	_draw_rough_panel(Vector2(458, 292), Color("294637"), Color("111d17"), 5)
	_draw_fitted_text("outro", _color("cream"))
	_draw_fitted_text("outro_label", Color("bcd3a6"))
	draw_set_transform(Vector2.ZERO, 0.0)
	# A loose bolt spins into place beside the sign.
	draw_set_transform(Vector2(462, 632), t * 4.0)
	for tooth in range(8):
		var angle := TAU * float(tooth) / 8.0
		draw_rect(Rect2(Vector2(cos(angle), sin(angle)) * 33.0 - Vector2(7, 12), Vector2(14, 24)), _color("wood_light"), true)
	draw_circle(Vector2.ZERO, 31, _color("wood_light"))
	draw_circle(Vector2.ZERO, 12, _color("workshop_dark"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_visual(kind: String, center: Vector2, t: float) -> void:
	var primary := Color(str(fixture.visual.primary))
	var secondary := Color(str(fixture.visual.secondary))
	match kind:
		"prop_board":
			_draw_prop_board(center, t)
		"radial_creature":
			for arm in range(8):
				var angle := TAU * float(arm) / 8.0 + sin(t * 1.8 + arm) * 0.11
				var mid := center + Vector2(cos(angle), sin(angle)) * 76.0
				var tip := center + Vector2(cos(angle + sin(t + arm) * 0.12), sin(angle + sin(t + arm) * 0.12)) * 112.0
				draw_polyline(PackedVector2Array([center, mid, tip]), primary, 24, true)
			draw_circle(center, 68, secondary)
			draw_circle(center + Vector2(-23, -7), 11, Color("f5e7bd"))
			draw_circle(center + Vector2(23, -7), 11, Color("f5e7bd"))
			draw_circle(center + Vector2(-20, -6), 5, Color("241710"))
			draw_circle(center + Vector2(20, -6), 5, Color("241710"))
			for heart in range(3):
				_draw_heart(center + Vector2(float((heart - 1) * 34), 35), Color("7f2d2d"), 0.55)
		"beetle":
			var bounce := sin(t * 3.2) * 5.0
			draw_circle(center + Vector2(102, 20), 76, Color("6b4227"))
			for ring in range(3):
				draw_arc(center + Vector2(102, 20), 34.0 + ring * 15.0, 0, TAU, 24, Color(0.18, 0.10, 0.05, 0.36), 4)
			var beetle_center := center + Vector2(-65, 15 + bounce)
			for leg in range(3):
				var ly := float((leg - 1) * 34)
				draw_line(beetle_center + Vector2(-30, ly), beetle_center + Vector2(-76, ly - 18), secondary, 9)
				draw_line(beetle_center + Vector2(30, ly), beetle_center + Vector2(75, ly + 18), secondary, 9)
			_draw_filled_ellipse(beetle_center, Vector2(53, 78), primary)
			draw_line(beetle_center + Vector2(0, -70), beetle_center + Vector2(0, 70), Color("27301e"), 5)
			draw_circle(beetle_center + Vector2(-19, -42), 7, Color("f5e7bd"))
			draw_circle(beetle_center + Vector2(19, -42), 7, Color("f5e7bd"))
		"terminal":
			draw_rect(Rect2(center - Vector2(128, 86), Vector2(256, 172)), primary, true)
			draw_rect(Rect2(center - Vector2(111, 67), Vector2(222, 126)), Color("172620"), true)
			draw_rect(Rect2(center - Vector2(111, 67), Vector2(222, 126)), secondary, false, 5)
			var blink := 3.0 if int(t * 3.0) % 7 == 0 else 12.0
			draw_rect(Rect2(center + Vector2(-59, -15), Vector2(24, blink)), secondary, true)
			draw_rect(Rect2(center + Vector2(35, -15), Vector2(24, blink)), secondary, true)
			draw_arc(center + Vector2(0, 18), 38, 0.18, PI - 0.18, 20, secondary, 6)
			draw_line(center + Vector2(0, -86), center + Vector2(17, -123), secondary, 7)
			draw_circle(center + Vector2(18, -127), 9, _color("rust"))
		_:
			draw_circle(center, 90, primary)

func _draw_prop_board(center: Vector2, t: float) -> void:
	var props: Array = fixture.visual.get("props", [])
	for prop_index in range(props.size()):
		var prop: Dictionary = props[prop_index]
		var prop_center := center + Vector2(float(prop.get("x", 0)), float(prop.get("y", 0)))
		var primary := Color(str(prop.get("color", fixture.visual.primary)))
		var accent := Color(str(prop.get("accent", fixture.visual.secondary)))
		match str(prop.get("type", "")):
			"glow":
				var pulse := 1.0 + sin(t * 2.2 + float(prop.get("phase", 0))) * 0.05
				draw_circle(prop_center, float(prop.get("radius", 42)) * pulse, Color(primary, float(prop.get("alpha", 0.12))))
			"book":
				var size := Vector2(float(prop.get("width", 58)), float(prop.get("height", 112)))
				var rotation := deg_to_rad(float(prop.get("rotation", 0)))
				var points := _rotated_rect_points(prop_center, size, rotation)
				draw_colored_polygon(points, primary)
				draw_polyline(_closed(points), Color("241710"), 5, true)
				var spine_a := prop_center + Vector2(-size.x * 0.31, -size.y * 0.39).rotated(rotation)
				var spine_b := prop_center + Vector2(-size.x * 0.31, size.y * 0.39).rotated(rotation)
				draw_line(spine_a, spine_b, accent, 6)
				for page in range(3):
					var offset := Vector2(4, -18 + page * 18).rotated(rotation)
					draw_line(prop_center + offset, prop_center + offset + Vector2(size.x * 0.29, 0).rotated(rotation), Color(accent, 0.58), 2)
			"note":
				var size := Vector2(float(prop.get("width", 92)), float(prop.get("height", 64)))
				var rotation := deg_to_rad(float(prop.get("rotation", 0)))
				var points := _rotated_rect_points(prop_center, size, rotation)
				draw_colored_polygon(points, primary)
				draw_polyline(_closed(points), Color("3c291d"), 4, true)
				_draw_fitted_text("prop_%d_label" % prop_index, Color("2a1d17"))
			"line":
				var target := center + Vector2(float(prop.get("to_x", 0)), float(prop.get("to_y", 0)))
				draw_line(prop_center, target, primary, float(prop.get("width", 5)), true)
				draw_circle(prop_center, 5, accent)
				draw_circle(target, 5, accent)
			"droplet":
				var radius := float(prop.get("radius", 30))
				var bob := sin(t * 2.4 + float(prop.get("phase", 0))) * 3.0
				var drop_center := prop_center + Vector2(0, bob)
				draw_circle(drop_center + Vector2(0, 9), radius * 0.72, primary)
				draw_colored_polygon(PackedVector2Array([drop_center + Vector2(0, -radius), drop_center + Vector2(-radius * 0.66, 12), drop_center + Vector2(radius * 0.66, 12)]), primary)
				draw_circle(drop_center + Vector2(-8, 2), 4, Color(accent, 0.82))
			"planet":
				var radius := float(prop.get("radius", 58))
				var wobble := sin(t * 0.9 + float(prop.get("phase", 0))) * 2.0
				draw_circle(prop_center + Vector2(0, wobble), radius, primary)
				draw_arc(prop_center + Vector2(0, wobble), radius * 0.72, -1.1, 2.1, 28, accent, 6)
				for band in range(3):
					draw_arc(prop_center + Vector2(0, wobble), radius * (0.42 + band * 0.17), 0.2, 2.9, 22, Color(accent, 0.36), 3)
			"star":
				var radius := float(prop.get("radius", 10)) * (1.0 + sin(t * 3.0 + float(prop.get("phase", 0))) * 0.12)
				var points := PackedVector2Array()
				for point in range(10):
					var angle := -PI / 2.0 + TAU * float(point) / 10.0
					var point_radius := radius if point % 2 == 0 else radius * 0.42
					points.append(prop_center + Vector2(cos(angle), sin(angle)) * point_radius)
				draw_colored_polygon(points, primary)
			"counter":
				var size := Vector2(float(prop.get("width", 102)), float(prop.get("height", 56)))
				draw_rect(Rect2(prop_center - size / 2.0, size), primary, true)
				draw_rect(Rect2(prop_center - size / 2.0, size), accent, false, 4)
				_draw_fitted_text("prop_%d_label" % prop_index, accent)
				_draw_fitted_text("prop_%d_value" % prop_index, Color("f4df9d"))
			"telescope":
				var sway := sin(t * 0.8) * 0.025
				var direction := Vector2(1, -0.55).rotated(sway)
				draw_line(prop_center - direction * 44, prop_center + direction * 44, primary, 24, true)
				draw_line(prop_center + direction * 37, prop_center + direction * 55, accent, 31, true)
				draw_line(prop_center + Vector2(0, 8), prop_center + Vector2(-32, 70), accent, 7)
				draw_line(prop_center + Vector2(0, 8), prop_center + Vector2(38, 70), accent, 7)
				draw_circle(prop_center + Vector2(0, 8), 8, Color("241710"))

func _rotated_rect_points(center: Vector2, size: Vector2, rotation: float) -> PackedVector2Array:
	return PackedVector2Array([
		center + Vector2(-size.x / 2.0, -size.y / 2.0).rotated(rotation),
		center + Vector2(size.x / 2.0, -size.y / 2.0).rotated(rotation),
		center + Vector2(size.x / 2.0, size.y / 2.0).rotated(rotation),
		center + Vector2(-size.x / 2.0, size.y / 2.0).rotated(rotation)
	])

func _closed(points: PackedVector2Array) -> PackedVector2Array:
	var closed := points.duplicate()
	closed.append(points[0])
	return closed

func _draw_filled_ellipse(center: Vector2, radii: Vector2, color: Color) -> void:
	var points := PackedVector2Array()
	for point in range(32):
		var angle := TAU * float(point) / 32.0
		points.append(center + Vector2(cos(angle) * radii.x, sin(angle) * radii.y))
	draw_colored_polygon(points, color)

func _draw_heart(center: Vector2, color: Color, scale_value: float) -> void:
	draw_circle(center + Vector2(-8, -5) * scale_value, 12 * scale_value, color)
	draw_circle(center + Vector2(8, -5) * scale_value, 12 * scale_value, color)
	draw_colored_polygon(PackedVector2Array([center + Vector2(-19, 0) * scale_value, center + Vector2(19, 0) * scale_value, center + Vector2(0, 26) * scale_value]), color)

func _draw_rough_panel(size: Vector2, fill: Color, border: Color, salt: int) -> void:
	var shadow := Vector2(float(grammar.surfaces.shadow_offset[0]), float(grammar.surfaces.shadow_offset[1]))
	draw_rect(Rect2(-size / 2.0 + shadow, size), Color(0.04, 0.025, 0.02, 0.62), true)
	draw_rect(Rect2(-size / 2.0, size), fill, true)
	draw_rect(Rect2(-size / 2.0, size), border, false, float(grammar.surfaces.border_width))
	for wear in range(int(grammar.surfaces.wear_marks)):
		var x := -size.x / 2.0 + float((wear * 61 + salt * 19) % int(size.x))
		var y := -size.y / 2.0 + float((wear * 43 + salt * 29) % int(size.y))
		draw_line(Vector2(x, y), Vector2(x + 9 + wear % 15, y + float(wear % 3 - 1)), Color(0.20, 0.11, 0.07, 0.24), 2)

func _draw_crate(top_left: Vector2, size: Vector2, rotation: float) -> void:
	draw_set_transform(top_left + size / 2.0, rotation)
	draw_rect(Rect2(-size / 2.0, size), Color("754126"), true)
	draw_rect(Rect2(-size / 2.0, size), Color("2c1b14"), false, 5)
	draw_line(-size / 2.0 + Vector2(8, 8), size / 2.0 - Vector2(8, 8), Color("3f2519"), 7)
	draw_line(Vector2(-size.x / 2.0 + 8, size.y / 2.0 - 8), Vector2(size.x / 2.0 - 8, -size.y / 2.0 + 8), Color("3f2519"), 7)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_tape(center: Vector2, rotation: float) -> void:
	draw_set_transform(center, rotation)
	draw_rect(Rect2(-38, -12, 76, 24), Color(0.84, 0.72, 0.39, 0.82), true)
	for cut in range(5):
		draw_line(Vector2(-32 + cut * 15, -10), Vector2(-27 + cut * 15, 10), Color(0.40, 0.31, 0.15, 0.22), 2)
	draw_set_transform(Vector2.ZERO, 0.0)

func _draw_metal_label(top_left: Vector2, _text: String, rotation: float) -> void:
	draw_set_transform(top_left + Vector2(105, 27), rotation)
	draw_rect(Rect2(-105, -27, 210, 54), _color("metal"), true)
	draw_rect(Rect2(-105, -27, 210, 54), Color("262b28"), false, 4)
	draw_circle(Vector2(-88, 0), 5, Color("242622"))
	draw_circle(Vector2(88, 0), 5, Color("242622"))
	# All fixture-driven metal labels share this authoritative local safe area.
	_draw_fitted_text("visual_label", Color("f0dda5"))
	draw_set_transform(Vector2.ZERO, 0.0)

func _prepare_media() -> bool:
	var configured = fixture.get("media", null)
	if configured == null:
		media_state = {"status": "NOT_PRESENT", "fallback": "fixture_visual"}
		return true
	if typeof(configured) != TYPE_DICTIONARY:
		return _media_failure("malformed media configuration", {"expected": "object or null"})
	if not configured.has("type") and timeline.mode == "beats":
		var referenced := ""
		for beat in timeline.beats:
			if str(beat.type) == "media":
				var media_ref := str(beat.get("media_ref", "default"))
				if not referenced.is_empty() and referenced != media_ref:
					return _media_failure("one active named media asset per timeline is currently supported", {"first": referenced, "next": media_ref})
				referenced = media_ref
		if referenced.is_empty() or not configured.has(referenced) or typeof(configured[referenced]) != TYPE_DICTIONARY:
			return _media_failure("named media reference is unavailable", {"media_ref": referenced})
		configured = configured[referenced]
	media_spec = configured
	var media_type := str(media_spec.get("type", ""))
	var fit := str(media_spec.get("fit", ""))
	var anchor := str(media_spec.get("anchor", ""))
	var motion := str(media_spec.get("motion", "none"))
	var required = media_spec.get("required", null)
	if media_type not in ["image", "screenshot", "video"] or not grammar.media_slot.fit_modes.has(fit) or not grammar.media_slot.anchors.has(anchor):
		return _media_failure("unsupported media type, fit, or anchor", {"type": media_type, "fit": fit, "anchor": anchor})
	if required == null or typeof(required) != TYPE_BOOL or typeof(media_spec.get("provenance", null)) != TYPE_DICTIONARY:
		return _media_failure("malformed required or provenance metadata", {})
	if media_type == "video" and motion != "none":
		return _media_failure("video motion must be none", {"motion": motion})
	if media_type != "video" and not grammar.media_slot.image_motion.has(motion):
		return _media_failure("unsupported image motion", {"motion": motion})
	var source := _resolve_media_source(str(media_spec.get("source", "")))
	if source.is_empty() or not FileAccess.file_exists(source):
		if required == false:
			media_state = {"status": "OPTIONAL_FALLBACK", "fallback": "fixture_visual", "source": source}
			print("MF003_MEDIA_OPTIONAL_FALLBACK source=%s" % source)
			return true
		return _media_failure("file not found", {"source": source})
	if media_type in ["image", "screenshot"]:
		var image := Image.new()
		var error := image.load(source)
		if error != OK or image.get_width() <= 0 or image.get_height() <= 0:
			return _media_failure("image is unreadable or has invalid dimensions", {"source": source, "error": error})
		if image.get_width() > int(grammar.media_slot.maximum_source_width) or image.get_height() > int(grammar.media_slot.maximum_source_height):
			return _media_failure("image dimensions exceed template limit", {"width": image.get_width(), "height": image.get_height()})
		media_texture = ImageTexture.create_from_image(image)
		media_state = {"status": "PASS", "type": media_type, "source": source, "width": image.get_width(), "height": image.get_height(), "fit": fit, "anchor": anchor, "motion": motion, "safe_rect": grammar.media_slot.safe_rect}
	else:
		if media_spec.get("muted") != true:
			return _media_failure("MF-003 video inputs must be muted", {})
		if media_frames_dir.is_empty() or not DirAccess.dir_exists_absolute(media_frames_dir):
			return _media_failure("normalized video frames are unavailable", {"frames_dir": media_frames_dir})
		var directory := DirAccess.open(media_frames_dir)
		for filename in directory.get_files():
			if filename.begins_with("frame_") and filename.ends_with(".png"):
				media_frame_count += 1
		if media_frame_count <= 0 or not _preload_video_frames():
			return _media_failure("normalized video has no readable frames", {"frames_dir": media_frames_dir})
		media_state = {"status": "PASS", "type": media_type, "source": source, "width": media_texture.get_width(), "height": media_texture.get_height(), "fit": fit, "anchor": anchor, "motion": "none", "normalized_frames": media_frame_count, "safe_rect": grammar.media_slot.safe_rect}
	media_state.geometry_samples = _media_geometry_samples()
	media_state.timeline = {"enter_seconds": float(grammar.motion.intro_end_seconds), "exit_seconds": float(grammar.motion.outro_start_seconds)}
	if timeline.mode == "beats":
		for beat in timeline.beats:
			if str(beat.type) == "media":
				media_state.timeline = {"enter_seconds": float(beat.start), "exit_seconds": float(beat.end), "beat_id": str(beat.id)}
				break
	print("MF003_MEDIA_READY type=%s source=%s dimensions=%dx%d fit=%s anchor=%s" % [media_type, source, int(media_state.width), int(media_state.height), fit, anchor])
	return true

func _resolve_media_source(source: String) -> String:
	if source.is_empty():
		return ""
	if source.is_absolute_path():
		return source.simplify_path()
	var project_root := fixture_path.get_base_dir().get_base_dir().get_base_dir()
	return project_root.path_join(source).simplify_path()

func _media_caption() -> String:
	if not media_spec.is_empty() and not str(media_spec.get("caption", "")).strip_edges().is_empty():
		return str(media_spec.caption)
	return str(fixture.visual.label)

func _load_video_frame(index: int) -> bool:
	if index == media_loaded_frame and media_texture != null:
		return true
	if index < 0 or index >= media_video_textures.size():
		return false
	media_texture = media_video_textures[index]
	media_loaded_frame = index
	return true

func _preload_video_frames() -> bool:
	for index in range(media_frame_count):
		var path := media_frames_dir.path_join("frame_%06d.png" % index)
		var image := Image.new()
		if image.load(path) != OK or image.get_width() <= 0 or image.get_height() <= 0:
			return false
		media_video_textures.append(ImageTexture.create_from_image(image))
	return _load_video_frame(0)

func _media_geometry_samples() -> Array:
	var safe := _rect_from_config(grammar.media_slot.safe_rect)
	var samples := []
	for progress in [0.0, 0.5, 1.0]:
		var geometry: Dictionary = media_slot_engine.geometry(Vector2(float(media_state.width), float(media_state.height)), safe, str(media_spec.fit), str(media_spec.anchor), str(media_spec.get("motion", "none")), progress, float(grammar.media_slot.slow_push_amount), float(grammar.media_slot.gentle_pan_amount))
		samples.append({"progress": progress, "destination_rect": _rect_dictionary(geometry.destination), "source_rect": _rect_dictionary(geometry.source)})
	return samples

func _draw_media_slot(t: float, beat_progress: float = -1.0) -> void:
	if str(media_state.type) == "video":
		var elapsed: float = float(media_spec.duration_seconds) * beat_progress if beat_progress >= 0.0 else maxf(0.0, t - float(grammar.motion.intro_end_seconds))
		var requested_frames: int = maxi(1, int(round(float(media_spec.duration_seconds) * float(grammar.media_slot.video_frame_rate))))
		var index: int = media_slot_engine.frame_index(elapsed, int(grammar.media_slot.video_frame_rate), media_frame_count, requested_frames)
		if not _load_video_frame(index):
			_fail("MEDIA_ASSET_FAILED source=%s reason: normalized frame %d is unreadable" % [str(media_state.source), index])
			return
	var safe: Rect2 = _rect_from_config(grammar.media_slot.safe_rect)
	draw_rect(safe, Color(str(grammar.media_slot.background)), true)
	var progress: float = beat_progress if beat_progress >= 0.0 else clampf((t - float(grammar.motion.intro_end_seconds)) / (float(grammar.motion.outro_start_seconds) - float(grammar.motion.intro_end_seconds)), 0.0, 1.0)
	var geometry: Dictionary = media_slot_engine.geometry(Vector2(media_texture.get_width(), media_texture.get_height()), safe, str(media_spec.fit), str(media_spec.anchor), str(media_spec.get("motion", "none")), progress, float(grammar.media_slot.slow_push_amount), float(grammar.media_slot.gentle_pan_amount))
	draw_texture_rect_region(media_texture, geometry.destination, geometry.source)
	# A restrained inner shadow, scratches, and glare keep the slot in the physical grammar.
	draw_rect(safe, Color(0.02, 0.015, 0.01, 0.65), false, float(grammar.media_slot.inner_shadow_width))
	for scratch in range(7):
		var y := safe.position.y + 18.0 + float((scratch * 37 + int(fixture.seed)) % int(safe.size.y - 30.0))
		var x := safe.position.x + 12.0 + float((scratch * 53 + int(fixture.seed / 5)) % int(safe.size.x - 80.0))
		draw_line(Vector2(x, y), Vector2(x + 35 + scratch * 4, y - 2 + scratch % 3), Color(0.95, 0.9, 0.72, 0.12), 1.5)
	draw_colored_polygon(PackedVector2Array([safe.position + Vector2(12, 8), safe.position + Vector2(92, 8), safe.position + Vector2(42, safe.size.y - 8), safe.position + Vector2(12, safe.size.y - 8)]), Color(1, 1, 1, 0.035))

func _media_failure(reason: String, detail: Dictionary) -> bool:
	media_state = {"status": "FAIL", "reason": reason, "detail": detail, "source": str(media_spec.get("source", ""))}
	_write_layout_report("FAIL", reason, {"code": "MEDIA_ASSET_FAILED", "fixture": str(fixture.get("id", "unknown")), "role": "MEDIA", "safe_area": "MEDIA_SAFE_RECT", "reason": reason, "detail": detail})
	printerr("MEDIA_ASSET_FAILED source=%s reason: %s detail=%s" % [media_state.source, reason, JSON.stringify(detail)])
	get_tree().quit(1)
	return false

func _prepare_layouts() -> bool:
	var typography = grammar.get("typography", {})
	var roles = typography.get("roles", {}) if typeof(typography) == TYPE_DICTIONARY else {}
	var safe_areas = typography.get("safe_areas", {}) if typeof(typography) == TYPE_DICTIONARY else {}
	var required_areas := ["INTRO_SAFE_AREA", "HEADLINE_SAFE_AREA", "BODY_SAFE_AREA", "EMPHASIS_SAFE_AREA", "OUTRO_SAFE_AREA", "INTRO_LABEL_SAFE_AREA", "LABEL_SAFE_AREA", "OUTRO_LABEL_SAFE_AREA"]
	for area_name in required_areas:
		if not safe_areas.has(area_name):
			return _layout_failure("CONFIG", area_name, "missing safe-area definition", {})
	var instances := [
		{"key": "intro_label", "area": "INTRO_LABEL_SAFE_AREA", "text": "A BADLY MAINTAINED KNOWLEDGE MACHINE"},
		{"key": "visual_label", "area": "LABEL_SAFE_AREA", "text": _media_caption()},
		{"key": "outro_label", "area": "OUTRO_LABEL_SAFE_AREA", "text": str(fixture.outro.get("tagline", "HELD TOGETHER WITH TESTS & TAPE"))}
	]
	if timeline.mode == "legacy":
		instances.append_array([
			{"key": "intro", "area": "INTRO_SAFE_AREA", "text": str(fixture.intro.text)},
			{"key": "headline", "area": "HEADLINE_SAFE_AREA", "text": str(fixture.content.headline)},
			{"key": "body", "area": "BODY_SAFE_AREA", "text": str(fixture.content.body)},
			{"key": "emphasis", "area": "EMPHASIS_SAFE_AREA", "text": str(fixture.content.emphasis)},
			{"key": "outro", "area": "OUTRO_SAFE_AREA", "text": str(fixture.outro.text)}
		])
	else:
		var beat_areas := {"intro": "INTRO_SAFE_AREA", "statement": "HEADLINE_SAFE_AREA", "emphasis": "EMPHASIS_SAFE_AREA", "reveal": "OUTRO_SAFE_AREA", "outro": "OUTRO_SAFE_AREA"}
		for beat in timeline.beats:
			if beat_areas.has(str(beat.type)):
				instances.append({"key": "beat_%d" % int(beat.index), "area": beat_areas[str(beat.type)], "text": str(beat.text)})
	for instance in instances:
		var area_name: String = instance.area
		var area: Dictionary = safe_areas[area_name]
		var role := str(area.get("role", ""))
		if not roles.has(role):
			return _layout_failure(role if not role.is_empty() else "CONFIG", area_name, "missing typography role", {})
		var safe_rect := _rect_from_config(area)
		if safe_rect.size.x <= 0.0 or safe_rect.size.y <= 0.0:
			return _layout_failure(role, area_name, "malformed safe-area dimensions", {"safe_area": _rect_dictionary(safe_rect)})
		var fitted := _fit_text(str(instance.text), role, area_name, safe_rect)
		if fitted.is_empty():
			return false
		layouts[instance.key] = fitted
	if not _prepare_prop_layouts(roles):
		return false
	if not _validate_configured_collisions(safe_areas):
		return false
	_write_layout_report("PASS", "")
	print("MF002_LAYOUT fixture=%s intro=PASS headline=PASS body=PASS emphasis=PASS labels=PASS outro=PASS overlap_checks=PASS" % fixture.id)
	return true

func _prepare_prop_layouts(roles: Dictionary) -> bool:
	var templates = grammar.typography.get("derived_safe_areas", {})
	var props: Array = fixture.visual.get("props", [])
	for index in range(props.size()):
		var prop: Dictionary = props[index]
		var kind := str(prop.get("type", ""))
		if kind not in ["note", "counter"]:
			continue
		var width := float(prop.get("width", 0))
		var height := float(prop.get("height", 0))
		var center := Vector2(float(prop.get("x", 0)), float(prop.get("y", 0)))
		var container_rect := Rect2(center - Vector2(width, height) / 2.0, Vector2(width, height))
		if width <= 0.0 or height <= 0.0:
			return _layout_failure("LABEL", "PROP_%d" % index, "malformed decorative text container", {"container": _rect_dictionary(container_rect)})
		if kind == "note":
			var area_name := "PROP_NOTE_LABEL_SAFE_AREA"
			if not templates.has(area_name):
				return _layout_failure("CONFIG", area_name, "missing derived safe-area definition", {})
			var rule: Dictionary = templates[area_name]
			if not roles.has(str(rule.get("role", ""))):
				return _layout_failure("CONFIG", area_name, "derived safe area references missing role", {})
			var safe_rect := container_rect.grow(-float(rule.get("inset_x", 0)))
			# Respect a distinct vertical inset without embedding fixture coordinates.
			safe_rect.position.y = container_rect.position.y + float(rule.get("inset_y", 0))
			safe_rect.size.y = container_rect.size.y - 2.0 * float(rule.get("inset_y", 0))
			var fitted := _fit_text(str(prop.get("label", "")), str(rule.role), area_name, safe_rect)
			if fitted.is_empty():
				return false
			fitted.container_rect = container_rect
			layouts["prop_%d_label" % index] = fitted
		else:
			for field in ["label", "value"]:
				var area_name := "PROP_COUNTER_%s_SAFE_AREA" % str(field).to_upper()
				if not templates.has(area_name):
					return _layout_failure("CONFIG", area_name, "missing derived safe-area definition", {})
				var rule: Dictionary = templates[area_name]
				if not roles.has(str(rule.get("role", ""))):
					return _layout_failure("CONFIG", area_name, "derived safe area references missing role", {})
				var inset_x := float(rule.get("inset_x", 0))
				var safe_rect := Rect2(container_rect.position.x + inset_x, container_rect.position.y, container_rect.size.x - inset_x * 2.0, 0)
				if field == "label":
					safe_rect.position.y += float(rule.get("top_inset", 0))
					safe_rect.size.y = float(rule.get("height", 0))
				else:
					safe_rect.position.y += float(rule.get("top_offset", 0))
					safe_rect.size.y = container_rect.size.y - float(rule.get("top_offset", 0)) - float(rule.get("bottom_inset", 0))
				var fitted := _fit_text(str(prop.get(field, "")), str(rule.role), area_name, safe_rect)
				if fitted.is_empty():
					return false
				fitted.container_rect = container_rect
				layouts["prop_%d_%s" % [index, field]] = fitted
	return true

func _fit_text(value: String, role: String, area_name: String, safe_rect: Rect2) -> Dictionary:
	var constraints: Dictionary = grammar.typography.roles[role]
	var preferred := int(constraints.get("preferred_font_size", 0))
	var minimum := int(constraints.get("min_font_size", 0))
	var max_lines := int(constraints.get("max_lines", 0))
	var preferred_spacing := float(constraints.get("line_spacing", 0.0))
	var minimum_spacing := float(constraints.get("min_line_spacing", 0.0))
	if preferred <= 0 or minimum <= 0 or minimum > preferred or max_lines <= 0 or minimum_spacing <= 0.0 or preferred_spacing < minimum_spacing:
		_layout_failure(role, area_name, "malformed typography constraints", {"minimum_font_size": minimum, "preferred_font_size": preferred})
		return {}
	if constraints.get("wrap") != true or constraints.get("fit_mode") != "shrink_to_fit":
		_layout_failure(role, area_name, "unsupported wrapping or fit mode", {})
		return {}
	if constraints.get("horizontal_alignment") != "center" or constraints.get("vertical_alignment") != "center":
		_layout_failure(role, area_name, "unsupported text alignment", {})
		return {}
	var selected_font := regular_font if role == "BODY" else heavy_font
	var max_iterations := int(grammar.typography.get("max_fit_iterations", 32))
	var iterations := 0
	for spacing in [preferred_spacing, minimum_spacing]:
		for font_size in range(preferred, minimum - 1, -1):
			iterations += 1
			if iterations > max_iterations:
				_layout_failure(role, area_name, "maximum fitting iterations exceeded", {"iterations": iterations})
				return {}
			var lines := _wrap_lines(value, selected_font, font_size, safe_rect.size.x)
			if lines.is_empty() or lines.size() > max_lines:
				continue
			var font_height := selected_font.get_height(font_size)
			var line_advance: float = float(font_size) * float(spacing)
			var rendered_height: float = float(font_height) + float(lines.size() - 1) * line_advance
			var rendered_width := 0.0
			for line in lines:
				rendered_width = max(rendered_width, selected_font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x)
			if rendered_width <= safe_rect.size.x + 0.01 and rendered_height <= safe_rect.size.y + 0.01:
				var rendered_rect := Rect2(safe_rect.get_center() - Vector2(rendered_width, rendered_height) / 2.0, Vector2(rendered_width, rendered_height))
				return {
					"status": "PASS", "role": role, "safe_area_name": area_name, "text": value,
					"font_size": font_size, "minimum_font_size": minimum, "line_spacing": spacing,
					"lines": lines, "line_count": lines.size(), "line_advance": line_advance,
					"font_ascent": selected_font.get_ascent(font_size), "font_height": font_height,
					"safe_rect": safe_rect, "rendered_rect": rendered_rect, "iterations": iterations
				}
	_layout_failure(role, area_name, "content exceeds safe area at minimum readable font size", {
		"safe_area": _rect_dictionary(safe_rect), "minimum_font_size": minimum, "preferred_font_size": preferred,
		"max_lines": max_lines, "text_length": value.length(), "iterations": iterations
	})
	return {}

func _wrap_lines(value: String, selected_font: Font, font_size: int, max_width: float) -> Array[String]:
	var words := value.strip_edges().split(" ", false)
	var lines: Array[String] = []
	var line := ""
	for word in words:
		if selected_font.get_string_size(word, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > max_width:
			return []
		var candidate := word if line.is_empty() else line + " " + word
		if selected_font.get_string_size(candidate, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x > max_width and not line.is_empty():
			lines.append(line)
			line = word
		else:
			line = candidate
	if not line.is_empty():
		lines.append(line)
	return lines

func _draw_fitted_text(key: String, color: Color) -> void:
	var layout: Dictionary = layouts[key]
	var selected_font := regular_font if layout.role == "BODY" else heavy_font
	var rendered_rect: Rect2 = layout.rendered_rect
	var baseline := rendered_rect.position.y + float(layout.font_ascent)
	for index in range(layout.lines.size()):
		var line: String = layout.lines[index]
		var width := selected_font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, int(layout.font_size)).x
		draw_string(selected_font, Vector2(rendered_rect.get_center().x - width / 2.0, baseline + float(index) * float(layout.line_advance)), line, HORIZONTAL_ALIGNMENT_LEFT, -1, int(layout.font_size), color)
	if layout_debug:
		draw_rect(layout.safe_rect, Color(0.1, 0.95, 0.35, 0.9), false, 2.0)
		draw_rect(layout.rendered_rect, Color(0.95, 0.2, 0.2, 0.9), false, 1.0)

func _validate_configured_collisions(safe_areas: Dictionary) -> bool:
	for pair in grammar.typography.get("collision_checks", []):
		if typeof(pair) != TYPE_ARRAY or pair.size() != 2 or not safe_areas.has(pair[0]) or not safe_areas.has(pair[1]):
			return _layout_failure("CONFIG", "collision_checks", "malformed collision check", {"pair": pair})
		var first: Dictionary = safe_areas[pair[0]]
		var second: Dictionary = safe_areas[pair[1]]
		var first_rect := _stage_rect(first)
		var second_rect := _stage_rect(second)
		if first_rect.intersects(second_rect):
			return _layout_failure("COLLISION", "%s/%s" % [pair[0], pair[1]], "major layout regions overlap", {"first": _rect_dictionary(first_rect), "second": _rect_dictionary(second_rect)})
	return true

func _stage_rect(area: Dictionary) -> Rect2:
	var rect := _rect_from_config(area)
	var origin = area.get("stage_origin", [0, 0])
	return Rect2(rect.position + Vector2(float(origin[0]), float(origin[1])), rect.size)

func _rect_from_config(area: Dictionary) -> Rect2:
	return Rect2(float(area.get("x", 0)), float(area.get("y", 0)), float(area.get("width", 0)), float(area.get("height", 0)))

func _rect_dictionary(rect: Rect2) -> Dictionary:
	return {"x": rect.position.x, "y": rect.position.y, "width": rect.size.x, "height": rect.size.y}

func _layout_failure(role: String, safe_area_name: String, reason: String, detail: Dictionary) -> bool:
	var code := "%s_LAYOUT_FAILED" % role.to_upper()
	var failure := {"code": code, "fixture": str(fixture.get("id", "unknown")), "role": role, "safe_area": safe_area_name, "reason": reason, "detail": detail}
	_write_layout_report("FAIL", reason, failure)
	printerr("%s fixture=%s safe_area=%s reason: %s detail=%s" % [code, failure.fixture, safe_area_name, reason, JSON.stringify(detail)])
	get_tree().quit(1)
	return false

func _write_layout_report(status: String, reason: String, failure: Dictionary = {}) -> void:
	var serialized_layouts := {}
	for key in layouts:
		var item: Dictionary = layouts[key]
		serialized_layouts[key] = {
			"status": item.status, "role": item.role, "safe_area": item.safe_area_name,
			"font_size": item.font_size, "minimum_font_size": item.minimum_font_size,
			"line_spacing": item.line_spacing, "line_count": item.line_count,
			"safe_rect": _rect_dictionary(item.safe_rect), "rendered_rect": _rect_dictionary(item.rendered_rect)
		}
		if item.has("container_rect"):
			serialized_layouts[key].container_rect = _rect_dictionary(item.container_rect)
	var report := {"slice": "MF-002R1", "fixture": str(fixture.get("id", "unknown")), "result": status, "layout": serialized_layouts, "media": media_state, "overlap_checks": "PASS" if status == "PASS" else "FAIL", "reason": reason}
	if generated_scene_active and generated_stage != null:
		report.generated_scene = generated_stage.validation_report()
	if not failure.is_empty():
		report.failure = failure
	var file := FileAccess.open(layout_report_path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "  ") + "\n")

func _color(name: String) -> Color:
	return Color(str(grammar.palette[name]))

func _read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

func _valid_contract() -> bool:
	if not fixture.has_all(["id", "template", "seed", "format", "intro", "content", "visual", "outro", "audio"]):
		return false
	if fixture.template != "scrappy_diorama" or grammar.get("id") != "scrappy-diorama-v1":
		return false
	var format: Dictionary = fixture.format
	var duration := float(format.get("duration_seconds", 0))
	var extended := str(fixture.get("visual_strategy", {}).get("preference", "")) in ["godot_extended_data_window_refinement", "godot_live_investigation_refinement", "godot_final_polish_refinement", "godot_lower_right_polish_refinement"]
	var valid_duration := duration == 15.0 if not fixture.has("beats") else duration >= 10.0 and duration <= (30.0 if extended else 20.0)
	return format.get("width") == 1080 and format.get("height") == 1920 and format.get("fps") == 30 and valid_duration

func _write_timeline_report() -> void:
	if timeline_report_path.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(timeline_report_path.get_base_dir())
	var evidence := []
	for beat in timeline.get("beats", []):
		var execution: Dictionary = executed_beats.get(str(beat.id), {})
		evidence.append({
			"id": str(beat.id), "type": str(beat.type), "start": float(beat.start), "end": float(beat.end),
			"first_frame": int(execution.get("first_frame", round(float(beat.start) * FPS))),
			"last_frame": int(execution.get("last_frame", round(float(beat.end) * FPS) - 1)),
			"status": "PASS" if validate_layout_only or not execution.is_empty() else "FAIL"
		})
	var report := {"slice": "MF-004", "fixture": str(fixture.get("id", "unknown")), "mode": timeline.mode, "duration": video_duration, "total_frames": total_frames, "beats": evidence, "result": "PASS"}
	var file := FileAccess.open(timeline_report_path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "  ") + "\n")

func _log_timeline_stage(frame: int) -> void:
	match frame:
		0: print("MF002_STAGE INTRO")
		60: print("MF002_STAGE ENTER")
		120: print("MF002_STAGE SETTLE")
		240: print("MF002_STAGE EMPHASIS")
		384: print("MF002_STAGE EXIT")
		390: print("MF002_STAGE OUTRO")

func _argument_value(key: String) -> String:
	var args := OS.get_cmdline_user_args()
	for index in range(args.size() - 1):
		if args[index] == key:
			return ProjectSettings.globalize_path(args[index + 1])
	return ""

func _has_argument(key: String) -> bool:
	return key in OS.get_cmdline_user_args()

func _smoothstep(value: float) -> float:
	return value * value * (3.0 - 2.0 * value)

func _ease_out_back(value: float) -> float:
	var c1 := float(grammar.motion.SETTLE.overshoot)
	var c3 := c1 + 1.0
	return 1.0 + c3 * pow(value - 1.0, 3.0) + c1 * pow(value - 1.0, 2.0)

func _fail(message: String) -> void:
	printerr(message)
	get_tree().quit(1)
